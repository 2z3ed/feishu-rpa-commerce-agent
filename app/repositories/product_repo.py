"""
Product Repository - Mock Implementation

Provides mock product data for testing.
"""
from typing import Optional, Dict, Any


class ProductRepository:
    """Mock product repository for testing."""
    
    def __init__(self):
        # Mock product database
        self._products = {
            'A001': {
                'sku': 'A001',
                'product_name': '示例商品 A001',
                'status': 'active',
                'inventory': 128,
                'price': 59.90,
                'platform': 'mock'
            },
            'A002': {
                'sku': 'A002',
                'product_name': '示例商品 A002',
                'status': 'inactive',
                'inventory': 0,
                'price': 99.00,
                'platform': 'mock'
            },
            'B001': {
                'sku': 'B001',
                'product_name': '示例商品 B001',
                'status': 'active',
                'inventory': 256,
                'price': 129.50,
                'platform': 'mock'
            }
        }
    
    def query_sku_status(self, sku: str, platform: str = 'mock') -> Optional[Dict[str, Any]]:
        """
        Query SKU status.
        
        Args:
            sku: SKU code
            platform: Platform (woo/odoo/mock)
            
        Returns:
            Product data dict or None if not found
        """
        return self._products.get(sku.upper())
    
    def update_price(self, sku: str, target_price: float, platform: str = 'mock') -> Optional[Dict[str, Any]]:
        """
        Update product price (mock implementation).
        
        Args:
            sku: SKU code
            target_price: New price
            platform: Platform (woo/odoo/mock)
            
        Returns:
            Update result dict with old_price, new_price, status or None if not found
        """
        sku_upper = sku.upper()
        if sku_upper not in self._products:
            return None
        
        old_price = self._products[sku_upper]['price']
        self._products[sku_upper]['price'] = target_price
        
        return {
            'sku': sku_upper,
            'old_price': old_price,
            'new_price': target_price,
            'status': 'success',
            'platform': platform
        }


# Singleton instance
product_repo = ProductRepository()
