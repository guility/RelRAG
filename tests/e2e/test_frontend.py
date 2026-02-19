"""E2E tests for frontend. Run: docker compose up -d && playwright install && pytest tests/e2e/ -v -m e2e."""

import pytest

pytestmark = pytest.mark.e2e


def _login(page, base_url):
    """Log in via Keycloak (testuser/testpass)."""
    page.goto(base_url)
    page.wait_for_load_state("networkidle")
    if "8080" in page.url or "keycloak" in page.url.lower():
        page.locator('input[name="username"]').fill("testuser")
        page.locator('input[name="password"]').fill("testpass")
        # Keycloak uses #kc-login (button) or input[type="submit"]
        login_btn = page.locator("#kc-login").or_(page.locator('input[type="submit"]'))
        login_btn.click()
        page.wait_for_url(lambda u: base_url in u, timeout=15000)
        page.wait_for_load_state("networkidle")


def test_index_page_loads(page, base_url):
    """Index page loads and shows RelRAG header after login."""
    _login(page, base_url)
    assert "RelRAG" in page.content()


def test_navigation_links(page, base_url):
    """Navigation links are present."""
    _login(page, base_url)
    assert page.get_by_role("link", name="Главная").is_visible()
    assert page.get_by_role("link", name="Конфигурации").is_visible()
    assert page.get_by_role("link", name="Коллекции").is_visible()
    assert page.get_by_role("link", name="Документ").is_visible()


def test_configurations_page(page, base_url):
    """Configurations page loads."""
    _login(page, base_url)
    page.get_by_role("link", name="Конфигурации").click()
    page.wait_for_load_state("networkidle")
    assert "Конфигурации" in page.content()


def test_collections_page(page, base_url):
    """Collections page loads."""
    _login(page, base_url)
    page.get_by_role("link", name="Коллекции").click()
    page.wait_for_load_state("networkidle")
    assert "Коллекции" in page.content()


def test_document_page(page, base_url):
    """Document upload page loads."""
    _login(page, base_url)
    page.get_by_role("link", name="Документ").click()
    page.wait_for_load_state("networkidle")
    assert "Загрузить документ" in page.content()


def test_theme_toggle_exists(page, base_url):
    """Theme toggle button exists."""
    _login(page, base_url)
    theme_btn = page.locator("#btnTheme")
    assert theme_btn.is_visible()
