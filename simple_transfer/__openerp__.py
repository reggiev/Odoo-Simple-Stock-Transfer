{
	'name': 'Simple Transfer',
	'version': '1.0',
    'images': ['static/description/main_screenshot.png'],
    'category':'Warehouse',
	'description': """
    
    
    Transfer stocks in Odoo the easiest way:
        * Create an easy transfer form.
        * Specify the source warehouse and destination warehouse.
        * Specify the products and the quantities.
        * Click the transfer button.
        
    During the process above the module automatically:
        * Checked the availability of stocks in the source warehouse
        * If available, the stocks are immediately reserved
        * The stock moves are automatically processed and transferred
        
    If you have questions/concerns, contact me at reggievaldez@outlook.com
    I am more than happy to assist you.
    
    
	""",
	'author': 'Reggie Valdez',
	'website': '',
	'depends' : ['base','product',
			     'stock', 
				],
	'data': [
        'warehouse_view.xml'
		],
	'demo': [],
	'installable': True,
	'auto_install': False,
}
