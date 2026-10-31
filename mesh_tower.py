"""
Mesh/Tower manager for SecureLocalChat
Adds: Hub/Tower mode, Public Frequencies, Emergency Broadcast, Topology tracking
Does NOT modify existing NetworkManager/DatabaseManager logic. Runs alongside.
"""

import json
import time
import threading
import uuid
from pathlib import Path

class MeshTowerManager:
    def __init__(self, network, database):
        self.network = network
        self.database = database
        self.lock = threading.RLock()

        # Roles
        self.role = "PEER"  # PEER | TOWER
        self.tower_id = None
        self.tower_name = None
        self.is_tower = False

        # Tower registry (other towers seen)
        self.known_towers = {}  # tower_id -> info
        # Topology links
        self.links = {}  # key -> {type: direct|via_tower, a,b,...}
        # Frequencies / public channels
        self.frequencies = {}  # freq_id -> {name, owner, members:set, created_at,...}
        # Emergency
        self.emergency_active = False
        self.emergency_until = 0
        self.emergency_data = {}

        # Config
        self.config_file = Path('data') / 'mesh_config.json'
        self.load_config()

        # Init default freq if none
        with self.lock:
            if not self.frequencies:
                fid = str(uuid.uuid4())
                self.frequencies[fid] = {
                    'id': fid,
                    'name': 'General',
                    'owner': self.network.username if self.network else None,
                    'members': set([self.network.username]) if self.network and self.network.username else set(),
                    'created_at': time.time(),
                    'desc': 'Public LAN frequency'
                }

    def load_config(self):
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                self.role = cfg.get('role', 'PEER')
                self.tower_id = cfg.get('tower_id')
                self.tower_name = cfg.get('tower_name')
                if self.role == 'TOWER':
                    if not self.tower_id:
                        self.tower_id = str(uuid.uuid4())
                    self.is_tower = True
                else:
                    self.is_tower = False
        except Exception as e:
            print(f"[MESH] load_config err: {e}")

    def save_config(self):
        try:
            Path('data').mkdir(parents=True, exist_ok=True)
            cfg = {
                'role': self.role,
                'tower_id': self.tower_id,
                'tower_name': self.tower_name
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=2)
        except Exception as e:
            print(f"[MESH] save_config err: {e}")

    def set_tower_mode(self, enable, name=None):
        with self.lock:
            if enable:
                self.role = 'TOWER'
                self.is_tower = True
                if not self.tower_id:
                    self.tower_id = str(uuid.uuid4())
                self.tower_name = name or f"TOWER-{self.tower_id[:6].upper()}"
            else:
                self.role = 'PEER'
                self.is_tower = False
                self.tower_name = None
            self.save_config()
        return self.get_tower_info()

    def get_tower_info(self):
        with self.lock:
            return {
                'is_tower': self.is_tower,
                'role': self.role,
                'tower_id': self.tower_id,
                'tower_name': self.tower_name,
                'local_ip': self.network.local_ip if self.network else None,
                'port': self.network.port if self.network else None,
                'username': self.network.username if self.network else None
            }

    def register_tower_seen(self, tower_id, info):
        if not tower_id or tower_id == self.tower_id:
            return
        with self.lock:
            self.known_towers[tower_id] = {
                **info,
                'last_seen': time.time()
            }
            # link between towers
            key = f"t2t:{min(self.tower_id or '', tower_id)}|{max(self.tower_id or '', tower_id)}"
            self.links[key] = {
                'type': 'tower-tower',
                'a': self.tower_id,
                'b': tower_id,
                'last_seen': time.time()
            }

    def build_topology(self):
        topo = {
            'me': {
                'username': self.network.username if self.network else None,
                'ip': self.network.local_ip if self.network else None,
                'role': self.role,
                'tower_id': self.tower_id,
                'tower_name': self.tower_name,
                'is_tower': self.is_tower
            },
            'nodes': [],
            'links': [],
            'towers': [],
            'time': time.time()
        }

        users = []
        if self.network and hasattr(self.network, 'get_online_users'):
            try:
                users = self.network.get_online_users()
            except:
                users = []

        with self.lock:
            # peers
            for u in users:
                topo['nodes'].append({
                    'id': u.get('username'),
                    'label': u.get('username'),
                    'ip': u.get('ip'),
                    'role': 'PEER',
                    'type': 'peer',
                    'encrypted': u.get('encrypted', False),
                    'last_seen': u.get('last_seen')
                })
            # self
            if self.network and self.network.username:
                topo['nodes'].append({
                    'id': self.network.username,
                    'label': self.network.username + ' (you)',
                    'ip': self.network.local_ip,
                    'role': self.role,
                    'type': 'self',
                    'tower_id': self.tower_id
                })

            # towers
            for tid, tinfo in self.known_towers.items():
                topo['towers'].append({
                    'id': tid,
                    'name': tinfo.get('name') or tid[:8],
                    'ip': tinfo.get('ip'),
                    'owner': tinfo.get('owner'),
                    'last_seen': tinfo.get('last_seen')
                })
            if self.is_tower and self.tower_id:
                topo['towers'].append({
                    'id': self.tower_id,
                    'name': self.tower_name,
                    'ip': self.network.local_ip,
                    'owner': self.network.username,
                    'self': True,
                    'last_seen': time.time()
                })

            # links peer-direct
            for u in users:
                uname = u.get('username')
                if not uname: continue
                topo['links'].append({
                    'source': self.network.username if self.network and self.network.username else 'me',
                    'target': uname,
                    'type': 'direct'
                })
            # tower links
            for k,v in self.links.items():
                if v['type'] == 'tower-tower':
                    topo['links'].append({
                        'source': v['a'],
                        'target': v['b'],
                        'type': 'tower-tower'
                    })
            # via tower
            if self.is_tower and self.network and self.network.username:
                for u in users:
                    uname = u.get('username')
                    if uname == self.network.username: continue
                    topo['links'].append({
                        'source': self.tower_id,
                        'target': uname,
                        'type': 'via-tower'
                    })
            elif not self.is_tower and self.tower_id:
                for u in users:
                    uname = u.get('username')
                    if uname == self.network.username: continue
                    topo['links'].append({
                        'source': uname,
                        'target': self.tower_id,
                        'type': 'via-tower'
                    })

        return topo

    # Frequencies
    def create_frequency(self, name, desc=''):
        fid = str(uuid.uuid4())
        with self.lock:
            self.frequencies[fid] = {
                'id': fid,
                'name': name.strip() or f'Freq-{fid[:4]}',
                'owner': self.network.username if self.network else None,
                'members': set([self.network.username]) if self.network and self.network.username else set(),
                'created_at': time.time(),
                'desc': desc.strip()
            }
        return self.frequencies[fid]

    def join_frequency(self, fid):
        with self.lock:
            if fid in self.frequencies and self.network and self.network.username:
                self.frequencies[fid]['members'].add(self.network.username)
                return True
        return False

    def leave_frequency(self, fid):
        with self.lock:
            if fid in self.frequencies and self.network and self.network.username:
                self.frequencies[fid]['members'].discard(self.network.username)
                return True
        return False

    def list_frequencies(self):
        out = []
        with self.lock:
            for fid, f in self.frequencies.items():
                out.append({
                    'id': f['id'],
                    'name': f['name'],
                    'owner': f['owner'],
                    'desc': f['desc'],
                    'count': len(f['members']),
                    'joined': self.network.username in f['members'] if self.network and self.network.username else False
                })
        return out

    def get_freq_members(self, fid):
        with self.lock:
            if fid in self.frequencies:
                return list(self.frequencies[fid]['members'])
        return []

    # Emergency
    def trigger_emergency(self, msg='EMERGENCY BROADCAST'):
        with self.lock:
            self.emergency_active = True
            self.emergency_until = time.time() + 60
            self.emergency_data = {
                'from': self.network.username if self.network else 'unknown',
                'msg': msg,
                'at': time.time(),
                'tower_id': self.tower_id
            }
        return self.emergency_data

    def clear_emergency(self):
        with self.lock:
            self.emergency_active = False
            self.emergency_until = 0
            self.emergency_data = {}
        return {'ok': True}

    def get_emergency(self):
        with self.lock:
            if self.emergency_active and time.time() > self.emergency_until:
                self.emergency_active = False
                self.emergency_data = {}
            return {
                'active': self.emergency_active,
                'data': self.emergency_data
            }

# singleton holder
_mesh = None

def init_mesh(network, database):
    global _mesh
    if _mesh is None:
        _mesh = MeshTowerManager(network, database)
    return _mesh

def get_mesh():
    global _mesh
    return _mesh
