import requests
base = 'http://localhost:9000/api/v1'
r = requests.post(f'{base}/users/login', json={'email':'testuser@crossaio.com','password':'Test1234!'})
token = r.json().get('access_token','')
h = {'Authorization': f'Bearer {token}'}

# 产品描述生成（真实 AI）
r = requests.post(base+'/products/descriptions/generate', headers=h, json={
    'product_name': 'USB-C 充电器 65W GaN 快充',
    'platform': 'amazon',
    'keywords': ['USB-C', 'GaN', '65W', '快充', '笔记本']
})
print('产品描述生成:', r.status_code)
if r.status_code == 200:
    d = r.json()
    print('标题:', d.get('title','')[:80])
    bullets = d.get('bullets',[])
    for i, b in enumerate(bullets[:3]):
        print(f'  卖点{i+1}:', b[:80])
else:
    print(r.text[:300])
