from flask import render_template, url_for
import pandas as pd
import csv
import logging
import sys
from hz2.models import *
from hz2 import app

# Initilizing logging
# Log Formatters
smlFMT = logging.Formatter(
    '%(asctime)s %(levelname)-8s %(message)s')
extFMT = logging.Formatter(
    '%(asctime)s %(levelname)-8s:%(name)s.%(funcName)s: %(message)s')
# Log Handlers
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
console.setFormatter(extFMT)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(console)

@app.route("/")
@app.route("/home")
def home_page():
    return render_template('home.html')

@app.route("/about")
def about():
    return render_template('about.html', title="About")

@app.route("/resources")
def resources():
    return render_template('resources.html', title="The Resources")

@app.route("/weapon/<weapon_id>")
def weapon_detail(weapon_id):
    weapon = Weapon.query.filter_by(id=weapon_id).first()
    log.info(f"Weapon id : {weapon_id} results: {weapon}")
    if weapon == None:
        log.info(f"Weapon was not found. Loading weapon not found page")
        return render_template('not_found.html',title='Weapon not found', thing='weapon')

    # Get the weapon requirements
    w_reqs = Weapon_requirement.query.filter_by(weapon_id=weapon.id).all()
    if len(w_reqs) == 0:
        return render_template('weapon.html', title=f"Weapon - {weapon.title}", weapon=weapon, headings=None)
    log.debug(f"weapon requirement results= {w_reqs}")

    log.info(f"Building list for panda")
    x_tmp_list=[]
    # Require at least 5 columns
    for x in range(0,6):
        x_tmp_list.append(['skip','Force minimum number of pivot columns',f'Level {x}',0])
    # Load weapon requirements
    for req in w_reqs:
        x_tmp_list.append([req.resource_id,req.resource.title,req.level,req.amt_required])

    log.debug(f"x_tmp_list:\n {x_tmp_list}")
    # Creating panda dataframe from weapon requirements
    log.info("Loading list into panda dataframe")
    x_tmp_df = pd.DataFrame(x_tmp_list, columns= ['resource_id','resource','level','amt_req'])
    log.debug(f"dataframe: {x_tmp_df}")

    # Pivot for totals colum and row
    log.info('Creating pivot table from dataframe')
    x_tmp_pivotTable = x_tmp_df.pivot_table(index=['resource','resource_id'],columns='level',values='amt_req', aggfunc=['sum'], margins=True, margins_name='Total').fillna(0).astype(int)
    log.debug(f"pivottable: {x_tmp_pivotTable}")

    # Transform pivot table with totals to a list - Step 1: Convert to csv string
    log.info('Transform pivot data: Step 1 - pivot table -> csv string')
    x_tmp_pivot_string = x_tmp_pivotTable.to_csv(quoting=csv.QUOTE_NONNUMERIC,float_format=None)
    del x_tmp_pivotTable
    log.debug(f"pivottable -> string: {x_tmp_pivot_string}")

    # Transform pivot table with totals to a list - Step 2: Convert csv string to list
    log.info('Transform pivot data: Step 2 - csv string -> list')
    x_tmp_pivot_list = list(csv.reader(x_tmp_pivot_string.split('\n')))
    del x_tmp_pivot_string
    log.debug(f"string -> list: {x_tmp_pivot_list}")

    # Transform pivot table with totals to a list - Step 3: Remove unnessary rows from
    log.info('Transform pivot data: Step 3 - Create table header. Transform table data')
    # last 2 rows are not needed. This is a total row, and a blank row.
    del x_tmp_pivot_list[len(x_tmp_pivot_list)-2:len(x_tmp_pivot_list)]

    # x_tmp_pivot_list[0] is not needed. This is the sum-sum row
    # x_tmp_pivot_list[1] Is the header for the table
    # x_tmp_pivot_list[2] is not needed. Second header type row
    tbl_data = []
    r_numb = 0
    for x in x_tmp_pivot_list:
        # r_numb 0, 2 are useless. x[1] is the 'weapon_id' (if 'skip' then skip)
        if r_numb == 0 or r_numb == 2 or x[1] == 'skip': # do not append
            log.debug(f"{r_numb} : Skipped : {x}")
        elif r_numb == 1: # here is the header
            log.debug(f"{r_numb} : Header : {x}")
            headings = x
            headings[0] = 'Resource'
            log.info(f"Table Header: {headings}")
        else: # this is data. Make it pretty
            log.debug(f"{r_numb} : MakePrtty : {x}")
            # Columns to transform start at 2
            for col in range(2,len(x)):
                orgVal = x[col]
                testVal = int(x[col])
                if testVal > 0:
                    # thousand seperator
                    x[col] = '{:,}'.format(testVal)
                else:
                    # No value for zero's
                    x[col] = ""

            tbl_data.append(x)
        r_numb +=1
    log.info(f"Table Data: {tbl_data}")
    log.info("Render the weapon page")
    return render_template('weapon.html', title=f"Weapon - {weapon.title}", weapon=weapon, header_row=headings, data=tbl_data)

@app.route("/resource/<id>")
def resource_detail(id):
    # Get the resource
    resource = Resource.query.filter_by(id=id).first()
    log.info(f"Resource id : {id} results: {resource}")
    if resource == None:
        log.debug(f"Load resource not found page")
        return render_template('not_found.html',title='Resource not found', thing='resource')

    # Get weapons which require this resource
    weapons = Weapon_requirement.query.filter_by(resource_id=id).all()
    if len(weapons) == 0:
        log.info(f"No weapons require this resource")
        return render_template('resource.html', title=f"Resource - {resource.title}", resource=resource, header_row=None)

    log.debug(f"results of weapons needed it weapons= {weapons}")

    log.info(f"Building list for panda")
    x_tmp_list=[]
    # Required to have 5 levels/columns with data
    for x in range(0,6):
        x_tmp_list.append(['skip','Force minimum number of pivot columns',f'Level {x}',0])

    # Load the results from the query
    for req in weapons:
        x_tmp_list.append([req.weapon_id,f"{req.weapon.title} ({req.weapon.type.title})",req.level,req.amt_required])

    log.debug(f"x_tmp_list:\n {x_tmp_list}")
    # Creating panda dataframe from weapon requirements
    log.info("Loading list into panda dataframe")
    x_tmp_df = pd.DataFrame(x_tmp_list, columns= ['weapon_id','weapon','level','amt_req'])
    log.debug(f"dataframe: {x_tmp_df}")

    # Pivot for totals colum and row
    log.info('Creating pivot table from dataframe')
    x_tmp_pivotTable = x_tmp_df.pivot_table(index=['weapon','weapon_id'],columns='level',values='amt_req', aggfunc=['sum'], margins=True, margins_name='Total').fillna(0).astype(int)
    log.debug(f"pivottable: {x_tmp_pivotTable}")

    # Transform pivot table with totals to a list - Step 1: Convert to csv string
    log.info('Transform pivot data: Step 1 - pivot table -> csv string')
    x_tmp_pivot_string = x_tmp_pivotTable.to_csv(quoting=csv.QUOTE_NONNUMERIC,float_format=None)
    log.debug(f"pivottable -> string: {x_tmp_pivot_string}")

    # Transform pivot table with totals to a list - Step 2: Convert csv string to list
    log.info('Transform pivot data: Step 2 - csv string -> list')
    x_tmp_pivot_list = list(csv.reader(x_tmp_pivot_string.split('\n')))
    log.debug(f"string -> list: {x_tmp_pivot_list}")

    # Transform pivot table with totals to a list - Step 3: Remove unnessary rows from
    log.info('Transform pivot data: Step 3 - Create table header. Transform table data')
    # last 2 rows are not needed. This is a total row, and a blank row.
    del x_tmp_pivot_list[len(x_tmp_pivot_list)-2:len(x_tmp_pivot_list)]

    # x_tmp_pivot_list[0] is not needed. This is the sum-sum row
    # x_tmp_pivot_list[1] Is the header for the table
    # x_tmp_pivot_list[2] is not needed. Second header type row
    tbl_data = []
    r_numb = 0
    for x in x_tmp_pivot_list:
        # r_numb 0, 2 are useless. x[1] is the 'weapon_id' (if 'skip' then skip)
        if r_numb == 0 or r_numb == 2 or x[1] == 'skip': # do not append
            log.debug(f"{r_numb} : Skipped : {x}")
        elif r_numb == 1: # here is the header
            log.debug(f"{r_numb} : Header : {x}")
            headings = x
            headings[0] = 'Weapon'
            log.info(f"Table Header: {headings}")
        else: # this is data. Make it pretty
            log.debug(f"{r_numb} : MakePrtty : {x}")
            # Columns to transform start at 2
            for col in range(2,len(x)):
                orgVal = x[col]
                testVal = int(x[col])
                if testVal > 0:
                    # thousand seperator
                    x[col] = '{:,}'.format(testVal)
                else:
                    # No value for zero's
                    x[col] = ""

            tbl_data.append(x)
        r_numb +=1
    log.info(f"Table Data: {tbl_data}")
    return render_template('resource.html', title=f"Resource - {resource.title}", resource=resource, header_row=headings, data=tbl_data)

@app.route("/weapons")
def weapons():
    return render_template('weapons.html', title="The Resources")
