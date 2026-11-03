"""商用合规页面 + 支付跳转修复的回归测试。"""
from fastapi.testclient import TestClient


def test_privacy_and_terms_pages_serve(client: TestClient):
    """隐私政策 / 服务条款页面可访问（GDPR 合规底座）。"""
    assert client.get("/privacy").status_code == 200
    assert client.get("/terms").status_code == 200
    assert "隐私政策" in client.get("/privacy").text
    assert "服务条款" in client.get("/terms").text


def test_workbench_footer_links_compliance_pages(client: TestClient):
    """工作台底部含隐私/条款/定价链接。"""
    html = client.get("/app").text
    assert 'href="/privacy"' in html
    assert 'href="/terms"' in html


def test_subscription_button_redirects_to_checkout(client: TestClient):
    """前端订阅按钮在 Stripe 模式下跳转收银台（修复：此前只做了本地模拟）。"""
    html = client.get("/app").text
    assert "window.location.href=r.checkout_url" in html
    assert "window.location.href=r.approve_url" in html
