# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt

def execute(filters=None):
	if not filters: filters = {}
	columns = get_columns()
	last_col = len(columns) - 1
	
	item_list = get_items(filters)
	item_tax, tax_accounts = get_tax_accounts(item_list, columns)
	
	data = []
	for d in item_list:
		row = [d.item_code, d.item_name, d.item_group, d.parent, d.posting_date, 
			d.customer_name, d.debit_to, d.territory, d.project_name, d.company, d.sales_order, 
			d.delivery_note, d.income_account, d.qty, d.basic_rate, d.amount]
			
		for tax in tax_accounts:
			row.append(item_tax.get(d.parent, {}).get(d.item_code, {}).get(tax, 0))
			
		row.append(sum(row[last_col:]))
		data.append(row)
	
	return columns, data
	
def get_columns():
	return [
		"Item Code:Link/Item:120", "Item Name::120", "Item Group:Link/Item Group:100", 
		"Invoice:Link/Sales Invoice:120", "Posting Date:Date:80", "Customer:Link/Customer:120", 
		"Customer Account:Link/Account:120", "Territory:Link/Territory:80",
		"Project:Link/Project:80", "Company:Link/Company:100", "Sales Order:Link/Sales Order:100", 
		"Delivery Note:Link/Delivery Note:100", "Income Account:Link/Account:140", 
		"Qty:Float:120", "Rate:Currency:120", "Amount:Currency:120"
	]
	
	
def get_conditions(filters):
	conditions = ""
	
	for opts in (("company", " and company=%(company)s"),
		("account", " and si.debit_to = %(account)s"),
		("item_code", " and si_item.item_code = %(item_code)s"),
		("from_date", " and si.posting_date>=%(from_date)s"),
		("to_date", " and si.posting_date<=%(to_date)s")):
			if filters.get(opts[0]):
				conditions += opts[1]

	return conditions
		
def get_items(filters):
	conditions = get_conditions(filters)
	return webnotes.conn.sql("""select si_item.parent, si.posting_date, si.debit_to, si.project_name, 
		si.customer, si.remarks, si.territory, si.company, si_item.item_code, si_item.item_name, 
		si_item.item_group, si_item.sales_order, si_item.delivery_note, si_item.income_account, 
		si_item.qty, si_item.basic_rate, si_item.amount, si.customer_name
		from `tabSales Invoice` si, `tabSales Invoice Item` si_item 
		where si.name = si_item.parent and si.docstatus = 1 %s 
		order by si.posting_date desc, si_item.item_code desc""" % conditions, filters, as_dict=1)
		
def get_tax_accounts(item_list, columns):
	import json
	item_tax = {}
	tax_accounts = []
	
	tax_details = webnotes.conn.sql("""select parent, account_head, item_wise_tax_detail
		from `tabSales Taxes and Charges` where parenttype = 'Sales Invoice' 
		and docstatus = 1 and ifnull(account_head, '') != ''
		and parent in (%s)""" % ', '.join(['%s']*len(item_list)), tuple([item.parent for item in item_list]))
		
	for parent, account_head, item_wise_tax_detail in tax_details:
		if account_head not in tax_accounts:
			tax_accounts.append(account_head)
		
		invoice = item_tax.setdefault(parent, {})
		if item_wise_tax_detail:
			try:
				item_wise_tax_detail = json.loads(item_wise_tax_detail)
				for item, tax_amount in item_wise_tax_detail.items():
					invoice.setdefault(item, {})[account_head] = flt(tax_amount)
				
			except ValueError:
				continue
	
	tax_accounts.sort()
	columns += [account_head + ":Currency:80" for account_head in tax_accounts]
	columns.append("Total:Currency:80")

	return item_tax, tax_accounts