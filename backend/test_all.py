import requests
base = 'http://localhost:9000/api/v1'
r = requests.post(f'{base}/users/login', json={'email':'testuser@crossaio.com','password':'Test1234!'})
token = r.json().get('access_token','')
h = {'Authorization': f'Bearer {token}'}

# 差评分析
r = requests.post(base+'/products/review-insights', headers=h, json={
    'product_name': 'USB-C 充电器 65W',
    'reviews': ['Stopped working after 2 weeks', 'Too hot to touch']
})
print('差评分析:', r.status_code, 'OK' if r.status_code==200 else r.text[:150])

# 自动化流水线
r = requests.post(base+'/automation/run', headers=h)
print('自动化流水线:', r.status_code)
if r.status_code==200:
    d = r.json()
    s = d.get('summary',{})
    pf = s.get('problems_found',0)
    gpsr = s.get('gpsr_blocks_ready',0)
    ar = s.get('auto_replies_sent',0)
    print('  发现问题:', pf, '合规块:', gpsr, '自动回复:', ar)

# 添加 Listing
r = requests.post(base+'/listings', headers=h, json={
    'product_name': 'USB-C 充电器 65W',
    'platform': 'amazon',
    'title': '65W GaN Fast Charger',
    'sku': 'USB-C-65W-001'
})
print('添加 Listing:', r.status_code, 'OK' if r.status_code==200 else r.text[:150])

# 跑监控
r = requests.post(base+'/watch/run', headers=h)
print('跑监控:', r.status_code, 'OK' if r.status_code==200 else r.text[:150])

# 写回列表
r = requests.get(base+'/automation/writeback', headers=h)
print('写回列表:', r.status_code, '待写回:', r.json().get('total',0) if r.status_code==200 else r.text[:100])

# 订阅状态
r = requests.get(base+'/billing/subscription', headers=h)
print('订阅状态:', r.status_code, r.json().get('plan','') if r.status_code==200 else r.text[:100])
