from flask_testing import TestCase

from ocrd_butler.config import TestingConfig
from ocrd_butler.factory import create_app


class ApiTests(TestCase):
    def create_app(self):
        return create_app(config=TestingConfig)

    def test_util_routes(self):
        response = self.client.get('/api/_util/routes')
        assert response.status_code == 200
        assert response.json.get(
            '/api/_util/routes'
        ) == 'GET, HEAD, OPTIONS'
