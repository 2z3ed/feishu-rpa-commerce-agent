import requests
from src.config import config


class WooCommerceClient:
    """WooCommerce API client"""
    
    def __init__(self):
        self.url = config.WOOCOMMERCE_URL
        self.consumer_key = config.WOOCOMMERCE_CONSUMER_KEY
        self.consumer_secret = config.WOOCOMMERCE_CONSUMER_SECRET
    
    def _request(self, method, endpoint, data=None):
        """Make API request"""
        url = f"{self.url}/wp-json/wc/v3{endpoint}"
        auth = (self.consumer_key, self.consumer_secret)
        
        if method == "get":
            response = requests.get(url, auth=auth, params=data)
        elif method == "post":
            response = requests.post(url, auth=auth, json=data)
        elif method == "put":
            response = requests.put(url, auth=auth, json=data)
        elif method == "delete":
            response = requests.delete(url, auth=auth)
        else:
            raise Exception(f"Unsupported method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    def get_products(self, params=None):
        """Get products"""
        return self._request("get", "/products", params)
    
    def get_product(self, product_id):
        """Get single product"""
        return self._request("get", f"/products/{product_id}")
    
    def update_product(self, product_id, data):
        """Update product"""
        return self._request("put", f"/products/{product_id}", data)
    
    def get_orders(self, params=None):
        """Get orders"""
        return self._request("get", "/orders", params)
    
    def get_order(self, order_id):
        """Get single order"""
        return self._request("get", f"/orders/{order_id}")
    
    def update_order(self, order_id, data):
        """Update order"""
        return self._request("put", f"/orders/{order_id}", data)