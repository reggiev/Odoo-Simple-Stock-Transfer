from datetime import datetime, date, time, timedelta
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.osv import osv

class SimpleStockTransferLine(models.Model):
    _name = 'simple.stock.transfer.line'
    
    @api.one
    def _get_uom(self):
        if self.product_id:
            self.transfer_uom = self.product_id.uom_id
    
    @api.one
    def _compute_price(self):
        if self.product_id:
            self.line_total_price = self.quantity * self.unit_price
    
    product_id = fields.Many2one('product.product', string="Product",required= True)
    quantity = fields.Float(string="Quantity",required= True, default=1.0)
    transfer_uom = fields.Many2one('product.uom', string="Transfer UOM", store=True, related='product_id.uom_id')
    
    unit_price = fields.Float(string="Unit Price",required= True, default=0.0)
    line_total_price = fields.Float(string="Subtotal", store=True)
    
    simple_stock_transfer_id = fields.Many2one('simple.stock.transfer', string="Simple Transfer Reference", ondelete='cascade', index=True)
    
    available_units = fields.Float(string="Available")
    
    @api.multi
    def get_quantity_at_location(self,warehouse_stock_location,product_id):
        sql = """select COALESCE( SUM(qty), 0) from stock_quant where location_id = %d and product_id = %d""" % (warehouse_stock_location, product_id)
        self._cr.execute(sql)
        return self._cr.fetchall()[0][0]
    
    @api.onchange('product_id','quantity','unit_price','line_total_price')
    def _check_line_change(self):
        self._get_uom()
        self._compute_price()
    
class SimpleStockTrasfer(models.Model):
    _name = 'simple.stock.transfer'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    
    def _assign_transfer_code(self):
        self.name =  self.pool['ir.sequence'].get(self.env.cr, self.env.uid, 'simple_transfer')
        return self
        
    partner_id = fields.Many2one('res.partner', string="Partner",track_visibility='onchange',required= True)
    source_location_id = fields.Many2one('stock.warehouse', string="Source Location",track_visibility='onchange',required= True)
    destination_location_id = fields.Many2one('stock.warehouse', string="Destination Location",track_visibility='onchange',required= True)
    
    move_type = fields.Selection(selection=[('internal_transfer', 'Internal Transfer'),('consignment','Consignment')], default='internal_transfer',track_visibility='onchange',required= True)
    
    name = fields.Char(track_visibility='onchange',default=lambda self: self.pool['ir.sequence'].get(self.env.cr, self.env.uid, 'simple_transfer'),required= True, compute='_assign_transfer_code')
    
    date = fields.Date(string="Date",track_visibility='onchange',required= True, default=date.today())
    state = fields.Selection(selection=[('draft', 'Draft'),('done','Done'),('cancelled', 'Cancelled')], default='draft',track_visibility='onchange',required= True)
    
    simple_stock_tranfer_line = fields.One2many('simple.stock.transfer.line', 'simple_stock_transfer_id', string="Simple Stock Tranfer Line")
    
    source_document = fields.Char(string="Source Document",track_visibility='onchange',required= True)
    remarks = fields.Text(string="Notes", track_visibility='onchange')
    
    @api.onchange('destination_location_id','source_location_id')
    def _check_change(self):
        # The source and destination location should not be the same
        if self.source_location_id.id == self.destination_location_id.id:
            self.destination_location_id = ''
            
    # Check if there is available stocks in the source location
    @api.multi
    def check_simple_stock_moves(self):
        if not self.simple_stock_tranfer_line:
            raise osv.except_osv(_('No products specified'),_(' Please specify some products to transfer.' ) )
            
        for simple_transfer_line in self.simple_stock_tranfer_line:
            current_stock = simple_transfer_line.get_quantity_at_location(self.source_location_id.lot_stock_id.id,simple_transfer_line.product_id.id)
             
            if simple_transfer_line.quantity > current_stock:
                query = """ update simple_stock_transfer set state = 'waiting_for_availability' 
where id = %s """%self.id
                self._cr.execute(query)
                print query
                raise osv.except_osv(_('Not Enough Stock'),_('You are trying to transfer %s of %s but you only have %s in location %s.'%(simple_transfer_line.quantity, simple_transfer_line.product_id.name,current_stock, self.source_location_id.name ) ))
                return True
        
        # If the execution went here it means that there is enough stock for the transfer.
        for simple_transfer_line in self.simple_stock_tranfer_line:
            if simple_transfer_line.quantity <= 0:
                raise osv.except_osv(_('Quantity Error'),_(' It appears that you have specified a wrong quantity in one of the products.' ) )
             
            #Make stock moves for each line then transfer them immeadiately
            vals = {
                 'product_id' : simple_transfer_line.product_id.id,
                 'product_uom_qty' : simple_transfer_line.quantity,
                 'name' : self.name +' ' + simple_transfer_line.product_id.name,
                 'location_id' : self.source_location_id.lot_stock_id.id,
                 'location_dest_id' :self.destination_location_id.lot_stock_id.id,
                 'product_uom' : simple_transfer_line.transfer_uom.id,
                 'origin': self.name
            }
            
            id = self.pool.get('stock.move').create(self.env.cr,self.env.uid,vals, context=None)
             
            for move in  self.pool.get('stock.move').browse(self.env.cr,self.env.uid,[id],context=None):
                move.action_confirm()
                move.action_assign()
                move.action_done()
            self.state = 'done'

                  
    