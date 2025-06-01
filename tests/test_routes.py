######################################################################
# Copyright 2016, 2023 John J. Rofrano. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
######################################################################
"""
Product API Service Test Suite
"""
import os
import logging
from decimal import Decimal
from unittest import TestCase
from service import app
from service.common import status
from service.models import db, init_db, Product
from tests.factories import ProductFactory
from urllib.parse import quote_plus

DATABASE_URI = os.getenv("DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres")
BASE_URL = "/products"

######################################################################
#  T E S T   C A S E S
######################################################################
class TestProductRoutes(TestCase):
    """Product Service tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Run once after all tests"""
        db.session.close()

    def setUp(self):
        """Runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()
        db.session.commit()

    def tearDown(self):
        db.session.remove()

    def _create_products(self, count: int = 1) -> list:
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    def test_index(self):
        """It should return the index page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(b"Product Catalog Administration", response.data)

    def test_health(self):
        """It should be healthy"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data['message'], 'OK')

    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)

    def test_create_product_with_no_name(self):
        """It should not Create a Product without a name"""
        product = self._create_products()[0]
        new_product = product.serialize()
        del new_product["name"]
        response = self.client.post(BASE_URL, json=new_product)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no Content-Type"""
        response = self.client.post(BASE_URL, data="bad data")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with wrong Content-Type"""
        response = self.client.post(BASE_URL, data={}, content_type="plain/text")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_duplicate_product(self):
        """It should allow creating duplicate Products if allowed"""
        product = self._create_products(1)[0]
        duplicate = product.serialize()
        response = self.client.post(BASE_URL, json=duplicate)
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_409_CONFLICT])

    def test_get_product(self):
        """It should Get a single Product"""
        test_product = self._create_products(1)[0]
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["name"], test_product.name)

    def test_get_product_not_found(self):
        """It should not Get a Product that's not found"""
        response = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_product_invalid_id(self):
        """It should not Get a Product with invalid ID format"""
        response = self.client.get(f"{BASE_URL}/invalid")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_product(self):
        """It should Update an existing Product"""
        test_product = ProductFactory()
        response = self.client.post(BASE_URL, json=test_product.serialize())
        new_product = response.get_json()
        new_product["description"] = "updated description"
        response = self.client.put(f"{BASE_URL}/{new_product['id']}", json=new_product)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_product = response.get_json()
        self.assertEqual(updated_product["description"], "updated description")

    def test_update_nonexistent_product(self):
        """It should not Update a non-existent Product"""
        fake_product = ProductFactory().serialize()
        fake_product["id"] = 99999
        response = self.client.put(f"{BASE_URL}/99999", json=fake_product)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_product(self):
        """It should Delete a Product"""
        products = self._create_products(1)
        product_id = products[0].id
        response = self.client.delete(f"{BASE_URL}/{product_id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get(f"{BASE_URL}/{product_id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_nonexistent_product(self):
        """It should return 404 when deleting a non-existent Product"""
        response = self.client.delete(f"{BASE_URL}/99999")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_product_list(self):
        """It should Get a list of Products"""
        self._create_products(5)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 5)

    def test_query_by_name(self):
        """It should Query Products by name"""
        products = self._create_products(5)
        test_name = products[0].name
        response = self.client.get(BASE_URL, query_string=f"name={quote_plus(test_name)}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        for product in data:
            self.assertEqual(product["name"], test_name)

    def test_query_by_category(self):
        """It should Query Products by category"""
        products = self._create_products(10)
        category = products[0].category.name
        response = self.client.get(BASE_URL, query_string=f"category={category}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        for product in data:
            self.assertEqual(product["category"], category)

    def test_query_by_availability(self):
        """It should Query Products by availability"""
        products = self._create_products(10)
        available_products = [p for p in products if p.available]
        response = self.client.get(BASE_URL, query_string="available=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), len(available_products))
        for product in data:
            self.assertTrue(product["available"])

    def test_query_by_category_and_availability(self):
        """It should Query Products by category and availability"""
        products = self._create_products(10)
        sample = products[0]
        query = f"category={sample.category.name}&available={'true' if sample.available else 'false'}"
        response = self.client.get(BASE_URL, query_string=query)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        for product in data:
            self.assertEqual(product["category"], sample.category.name)
            self.assertEqual(product["available"], sample.available)

    def get_product_count(self):
        """Returns current product count"""
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return len(response.get_json())
    
    def test_delete_nonexistent_product(self):
        """It should return 404 when deleting a non-existent Product"""
        response = self.client.delete(f"{BASE_URL}/99999")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
