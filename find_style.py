with open('templates/chat.html', encoding='utf-8') as f:
    c = f.read()
# find style block
idx = c.find('<style>')
end = c.find('</style>')
print('style block length:', end-idx)
with open('out.txt', 'w', encoding='utf-8') as f:
    f.write(c[idx:end+8])