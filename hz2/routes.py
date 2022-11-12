from flask import render_template, url_for, make_response, send_file
import pandas as pd
import sys
import csv, io, json, xlsxwriter
import logging
from hz2.models import *
from hz2 import app

log = logging.getLogger(__name__)

def get_weapon_detail(id):
    """Get and return weapon detail information

    Args:
        id (int): The weapon's id to get data for

    Returns:
        dictionary :
        key weapon (list of weapon data)
        key header_row (list of the column headers)
        key data (list of resources to upgrade weapon)
    """
    tmp_dict = {}
    tmp_dict['weapon'] = None
    tmp_dict['header_row'] = None
    tmp_dict['data'] = None

    tmp_dict['weapon'] = Weapon.query.filter_by(id=id).first()
    log.info(f"weapon_id:{id} results: {tmp_dict['weapon']}")

    if tmp_dict['weapon'] == None:
        log.debug(f'weapon_id:{id} not found. Returning {tmp_dict}')
        return tmp_dict

    # Get the weapon requirements
    w_reqs = Weapon_requirement.query.filter_by(weapon_id=tmp_dict['weapon'].id).all()
    if len(w_reqs) == 0:
        log.info(f"weapon_id:{id} has no resource requirements. Returning {tmp_dict}")

        return tmp_dict

    log.info(f"weapon_id:{id} requires {len(w_reqs)} resources")
    log.info(f"Building weapon_id:{id} list for panda")
    x_tmp_list=[]
    # Require at least 5 columns
    for x in range(0,6):
        x_tmp_list.append(['skip','Force minimum number of pivot columns',f'Level {x}',0])
    # Load weapon requirements
    for req in w_reqs:
        x_tmp_list.append([req.resource_id,req.resource.title,req.level,req.amt_required])

    log.debug(f"weapon_id:{id} x_tmp_list:\n{x_tmp_list}")
    # Creating panda dataframe from weapon requirements
    log.info(f"Loading weapon_id:{id} list into panda dataframe")
    x_tmp_df = pd.DataFrame(x_tmp_list, columns= ['resource_id','resource','level','amt_req'])
    log.debug(f"weapon_id:{id} dataframe:\n{x_tmp_df}")

    # Pivot for totals colum and row
    log.info(f'Creating weapon_id:{id} pivot table from dataframe')
    x_tmp_pivotTable = x_tmp_df.pivot_table(index=['resource','resource_id'],columns='level',values='amt_req', aggfunc=['sum'], margins=True, margins_name='Total').fillna(0).astype(int)
    log.debug(f"weapon_id:{id} pivottable:\n{x_tmp_pivotTable}")

    # Transform pivot table with totals to a list - Step 1: Convert to csv string
    log.info(f'Transform weapon_id:{id} pivot data: Step 1 - pivot table -> csv string')
    x_tmp_pivot_string = x_tmp_pivotTable.to_csv(quoting=csv.QUOTE_NONNUMERIC,float_format=None)
    del x_tmp_pivotTable
    log.debug(f"weapon_id:{id} pivottable -> string:\n{x_tmp_pivot_string}")

    # Transform pivot table with totals to a list - Step 2: Convert csv string to list
    log.info(f'Transform weapon_id:{id} pivot data: Step 2 - csv string -> list')
    x_tmp_pivot_list = list(csv.reader(x_tmp_pivot_string.split('\n')))
    del x_tmp_pivot_string
    log.debug(f"weapon_id:{id} string -> list: {x_tmp_pivot_list}")

    # Transform pivot table with totals to a list - Step 3: Remove unnessary rows from
    log.info(f'Transform weapon_id:{id} pivot data: Step 3 - Create table header. Transform table data')
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
            headings[1] = 'Resource_id'
            headings[2] = 'Acquire'
            log.debug(f"Table Header: {headings}")
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

    tmp_dict['header_row'] = headings
    tmp_dict['data'] = tbl_data
    log.info(f"weapon_id:{id} data. Returning {tmp_dict}")
    return tmp_dict

def get_resource_detail_weapon(id):
    """Get resource_detail and weapons that require resourse

    Args:
        id (int): The weapon id of the weapon to get data for

    Returns:
        dictionary :
        key resource (list of resource data)
        key header_row (list of the column headers)
        key data (list of the data)
    """
    tmp_dict = {}
    tmp_dict['resource'] = None
    tmp_dict['header_row'] = None
    tmp_dict['data'] = None

    # Get the resource
    tmp_dict['resource'] = Resource.query.filter_by(id=id).first()
    log.info(f"resource_id: {id} results: {tmp_dict['resource']}")
    if tmp_dict['resource'] == None:
        log.debug(f'resource_id:{id} not found. Returning {tmp_dict}')

    # Get weapons which require this resource
    weapons = Weapon_requirement.query.filter_by(resource_id=id).all()
    log.debug(f'resource_id:{id} weapon query results:{weapons}')
    if len(weapons) == 0:
        log.info(f"resource_id:{id} has no weapons require it")
        return tmp_dict

    log.info(f"resource_id:{id} is used by: {len(weapons)} weapons")
    log.info(f"Building resource_id:{id} list for panda")
    x_tmp_list=[]
    # Required to have 5 levels/columns with data
    for x in range(0,6):
        x_tmp_list.append(['skip','Force minimum number of pivot columns',f'Level {x}',0])

    # Load the results from the query
    for req in weapons:
        x_tmp_list.append([req.weapon_id,f"{req.weapon.title} ({req.weapon.type.title})",req.level,req.amt_required])

    log.debug(f"resource_id:{id} x_tmp_list:\n {x_tmp_list}")
    # Creating panda dataframe
    log.info(f"Loading resource_id:{id} list into panda dataframe")
    x_tmp_df = pd.DataFrame(x_tmp_list, columns= ['weapon_id','weapon','level','amt_req'])
    log.debug(f"resource_id:{id} dataframe: {x_tmp_df}")

    # Pivot for totals colum and row
    log.info(f'Creating resource_id:{id} pivot table from dataframe')
    x_tmp_pivotTable = x_tmp_df.pivot_table(index=['weapon','weapon_id'],columns='level',values='amt_req', aggfunc=['sum'], margins=True, margins_name='Total').fillna(0).astype(int)
    log.debug(f"resource_id:{id} pivottable: {x_tmp_pivotTable}")

    # Transform pivot table with totals to a list - Step 1: Convert to csv string
    log.info('Transform resource_id:{id} pivot data: Step 1 - pivot table -> csv string')
    x_tmp_pivot_string = x_tmp_pivotTable.to_csv(quoting=csv.QUOTE_NONNUMERIC,float_format=None)
    log.debug(f"resource_id:{id} pivottable -> string: {x_tmp_pivot_string}")

    # Transform pivot table with totals to a list - Step 2: Convert csv string to list
    log.info(f'Transform resource_id:{id} pivot data: Step 2 - csv string -> list')
    x_tmp_pivot_list = list(csv.reader(x_tmp_pivot_string.split('\n')))
    log.debug(f"resource_id:{id} string -> list: {x_tmp_pivot_list}")

    # Transform pivot table with totals to a list - Step 3: Remove unnessary rows from
    log.info(f'Transform resource_id:{id} pivot data: Step 3 - Create table header. Transform table data')
    # last row is not needed as it's blank. (Want to keep the total row)
    del x_tmp_pivot_list[len(x_tmp_pivot_list)-1:len(x_tmp_pivot_list)]

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
            headings[1] = 'Weapon_id'
            headings[2] = 'Acquire'
            log.debug(f"Table Header: {headings}")
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
    tmp_dict['header_row'] = headings
    tmp_dict['data'] = tbl_data
    log.info(f'resource_id:{id} data. Return {tmp_dict}')
    return tmp_dict

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
    log.info(f"Fetching weapon detail for weapon_id:{weapon_id}")
    w_details = get_weapon_detail(weapon_id)
    log.info(f"Results of fetching weapon detail for weapon_id:{weapon_id} results:{w_details}")

    if  w_details['weapon'] == None:
        log.info(f"weapon_id:{weapon_id} - Weapon was not found. Loading weapon not found page")
        response = make_response(render_template('not_found.html',title='Weapon not found', thing="weapon"), 404)
        return response

    if w_details['data'] == None:
        log.info(f"weapon_id:{weapon_id} no resources required to upgrade")
        return render_template('weapon.html', title=f"Weapon - {w_details['weapon'].title}", weapon=w_details['weapon'], headings=None)

    return render_template('weapon.html', title=f"Weapon - {w_details['weapon'].title}", weapon=w_details['weapon'], header_row=w_details['header_row'], data=w_details['data'])

@app.route("/resource/<id>")
def resource_detail(id):
    log.info(f"Fetching resource detail for resource_id:{id}")
    r_details = get_resource_detail_weapon(id)
    log.info(f"Results of fetching resource_id:{id} results: {r_details}")

    if r_details['resource'] == None:
        log.info(f"resource_id:{id} - Resource was not found. Loading resource not found page")
        response = make_response(render_template('not_found.html',title='Resource not found', thing="Resource"), 404)
        return response

    if r_details['data'] == None:
        log.info(f"No weapons require this resource")
        return render_template('resource.html', title=f"Resource - {r_details['resource'].title}", resource=r_details['resource'], header_row=None)

    return render_template('resource.html', title=f"Resource - {r_details['resource'].title}", resource=r_details['resource'], header_row=r_details['header_row'], data=r_details['data'])

@app.route("/allweapons")
def weapons_all():
    # Get all the weapons in the db
    log.info(f"Getting all weapons")
    results = db.session.query(Weapon,Weapon_type,Rarity).join(Weapon_type,Rarity).with_entities(Weapon.id, Weapon.title,Weapon_type.id,Weapon_type.title, Rarity.id, Rarity.title).order_by(Weapon.title).all()
    log.info(f"Weapons found: {len(results)}")
    if len(results) == 0:
        log.critical(f"No weapons found in database")
        return render_template('not_found.html',title='Weapons not found', thing='weapons')
    log.debug(f"weapons: {results}")

    header = ("Weapon", "Type", "Rarity")
    data = results
    log.debug(f"Table Data: {data}")
    log.info(f"Loading weapons page with data")
    return render_template('weapons.html', title=f"ALL Weapons", header_row=header, data=data)

@app.route("/allresources")
def resources_all():
    # Get all the resources in the db
    log.info(f"Getting all resources")
    results = db.session.query(Resource,Resource_type,Rarity).join(Resource_type,Rarity).with_entities(Resource.id, Resource.title,Resource_type.id,Resource_type.title, Rarity.id, Rarity.title).order_by(Resource.title).all()
    log.info(f"Resources found: {len(results)}")
    if len(results) == 0:
        log.critical(f"No resources found in database")
        return render_template('not_found.html',title='Resources not found', thing='resource')
    log.debug(f"resources: {results}")

    header = ("Resource", "Type", "Rarity")
    data = results
    log.debug(f"Table Data: {data}")
    log.info(f"Loading resources page with all resources data")
    return render_template('resources.html', title=f"ALL Resources", header_row=header, data=data)

@app.route("/download/weapon/json/<id>")
def json_weapon_detail(id):
    """Display weapon detail data in json format

    Args:
        id (int): The weapon_id
    """
    log.info(f"Request for json data for weapon_id:{id}")
    w_details = get_weapon_detail(id)

    if w_details['weapon'] == None:
        log.info(f"weapon_id:{id} - Weapon was not found. Loading weapon not found page")
        response = make_response(render_template('not_found.html',title='Weapon not found', thing="weapon"), 404)
        return response

    if w_details['data'] == None:
        log.info(f"weapon_id:{id} no resources required to upgrade")
        return render_template('weapon.html', title=f"Weapon - {w_details['weapon'].title}", weapon=w_details['weapon'], headings=None)

    # dictionary to hold data for json conversion
    w_dict = {}
    w_dict['weapon_id'] = w_details['weapon'].id
    w_dict['weapon_name'] = w_details['weapon'].title
    w_dict['type'] = w_details['weapon'].type.title
    w_dict['rarity'] = w_details['weapon'].rarity.title

   # Update w_dict['resources'] for json conversion
    w_dict['resources'] = []
    for row in w_details['data']:
        x=0
        xtmp={}
        first_i = True # We are at the first item in the row
        for key in w_details['header_row']:
            if first_i:
                row_value = row[x]
                first_i = False
            else:
                # Expecting number else it's null
                xrow_value= row[x].replace(',','')
                if xrow_value.isnumeric():
                    row_value=int(xrow_value)
                else:
                    row_value= None
            xtmp[key] = row_value
            x += 1
        w_dict['resources'].append(xtmp)

    json_string = json.dumps(w_dict)
    log.info(f"w_dict for json: {w_dict}")
    log.info(f"Weapon json: {json_string}")
    data_extract = io.BytesIO()
    data_extract.write(json_string.encode('utf-8'))
    data_extract.seek(0)  # seek stream on begin to retrieve all data from it
    return send_file(
        data_extract,
        mimetype='application/json',
        as_attachment=True,
        download_name=f'weapon_extract_{id}.json'
    )

@app.route("/download/resource/<id>")
def dwnload_resource_detail(id):
    log.info(f"Request to download resource_id:{id}")
    r_details = get_resource_detail_weapon(id)

    if r_details['resource'] == None:
        log.info(f"resource_id:{id} - Resource was not found. Loading resource not found page")
        response = make_response(render_template('not_found.html',title='Resource not found', thing="Resource"), 404)
        return response

    if r_details['data'] == None:
        log.info(f"No weapons require this resource")
        return render_template('resource.html', title=f"Resource - {r_details['resource'].title}", resource=r_details['resource'], header_row=None)

    log.info(f"Setup the download of resource detail for weapons")
    data_proxy = io.StringIO()
    csvwriter = csv.writer(data_proxy,dialect='excel')
    # Write the header row
    csvwriter.writerow(r_details['header_row'])
    # Write data rows
    csvwriter.writerows(r_details['data'])

    data_extract = io.BytesIO()
    data_extract.write(data_proxy.getvalue().encode('utf-8'))
    data_extract.seek(0)
    data_proxy.close()

    return send_file(
        data_extract,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'resource_extract_{id}.csv'
    )

@app.route("/download/resource/xlsx/<id>")
def xlsx_resource_detail(id):
    log.info(f"Request for xlsx for resource_id:{id}")
    r_details = get_resource_detail_weapon(id)

    if r_details['resource'] == None:
        log.info(f"resource_id:{id} - Resource was not found. Loading resource not found page")
        response = make_response(render_template('not_found.html',title='Resource not found', thing="resource"), 404)
        return response

    if r_details['header_row'] == None:
        ttl_weapons = 0
    else:
        ttl_weapons = len(r_details['data']) - 1

    data_extract = io.BytesIO()
    book = xlsxwriter.Workbook(data_extract)
    resource_sheet = book.add_worksheet("Resource")
    resource_sheet.set_column('A:A',15)

    # Settng the column B's width on resource sheet
    col_width = len('Resource Name') + 5
    if len(r_details['resource'].title) > col_width:
        col_width = len(r_details['resource'].title)
    resource_sheet.set_column('B:B',col_width)

    resource_sheet.set_column('C:C',len(r_details['resource'].type.title))

    # Settng the column D's width
    col_width = len('Rarity') + 5
    if len(r_details['resource'].rarity.title) > col_width:
        col_width = len(r_details['resource'].rarity.title)
    resource_sheet.set_column('D:D',col_width)
    resource_sheet.set_column('E:E',len("Total Weapons") + 2)

    resource_sheet.write_row("A1",["Resource ID",
        "Resource Name",
        "Type",
        "Rarity",
        "Total Weapons"],
        book.add_format({'bold': True}))

    resource_sheet.write_row("A2",[r_details['resource'].id,
        r_details['resource'].title,
        r_details['resource'].type.title,
        r_details['resource'].rarity.title,
        ttl_weapons])

    weapons_sheet = book.add_worksheet("Weapons")
    if ttl_weapons == 0:
        weapons_sheet.write("A1","No weapons require the resource",book.add_format({'bold': True}))
    else:
        weapons_sheet.write_row("A1",r_details['header_row'],book.add_format({'bold': True}))
        sheet_row = 1
        sheet_col = 0
        # Set default max width for Resource Column
        weapon_width = 15
        # write the weapons to which use this resource
        for row in r_details['data']:
            log.debug(f'resource_id:{id} sheet_row:{sheet_row}, sheet_col:{sheet_col}, {row}')
            first_i = True
            for i in row:
                if first_i: # this will be text
                    if len(i) > weapon_width:
                        weapon_width = len(i) + 3
                    weapons_sheet.write(sheet_row,sheet_col,i)
                    first_i = False
                else: # Assuming the rest will be numbers. Have to remove comma
                    tmp = i.replace(',','')
                    if tmp.isnumeric():
                        weapons_sheet.write(sheet_row,sheet_col,int(tmp))
                    else:
                        weapons_sheet.write(sheet_row,sheet_col,i)
                sheet_col +=1
            sheet_col = 0
            sheet_row += 1

        log.debug(f"resource_id:{id} Setting column A's width to: {weapon_width}")
        weapons_sheet.set_column("A:A", weapon_width)
        weapons_sheet.set_column("B:B",13) # Setting Resource ID column width

    book.close()  # close book and save it in "output"
    data_extract.seek(0)  # seek stream on begin to retrieve all data from it
    download_name=f'resource_extract_{id}.xlsx'
    log.info(f"resource_id:{id} - Response to download file: {download_name}")
    return send_file(
        data_extract,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=download_name
    )

@app.route("/download/weapon/xlsx/<id>")
def xlsx_weapon_detail(id):
    log.info(f"Request for xlsx for weapon_id:{id}")
    w_details = get_weapon_detail(id)

    if w_details['weapon'] == None:
        log.info(f"weapon_id:{id} - Weapon was not found. Loading weapon not found page")
        response = make_response(render_template('not_found.html',title='Weapon not found', thing="weapon"), 404)
        return response

    if w_details['header_row'] == None:
        ttl_resources = 0
    else:
        ttl_resources = len(w_details['data'])

    data_extract = io.BytesIO()
    book = xlsxwriter.Workbook(data_extract)
    weapon_sheet = book.add_worksheet("Weapon")
    weapon_sheet.set_column('A:A',15)

    # Settng the column B's width on weapons sheet
    col_width = len('Weapon Name') + 5
    if len(w_details['weapon'].title) > col_width:
        col_width = len(w_details['weapon'].title)
    weapon_sheet.set_column('B:B',col_width)

    weapon_sheet.set_column('C:C',len(w_details['weapon'].type.title))

    # Settng the column D's width
    col_width = len('Rarity') + 5
    if len(w_details['weapon'].rarity.title) > col_width:
        col_width = len(w_details['weapon'].rarity.title)
    weapon_sheet.set_column('D:D',col_width)
    weapon_sheet.set_column('E:E',len("Total Resources") + 2)

    weapon_sheet.write_row("A1",["Weapon ID",
        "Weapon Name",
        "Type",
        "Rarity",
        "Total Resources"],
        book.add_format({'bold': True}))

    weapon_sheet.write_row("A2",[w_details['weapon'].id,
        w_details['weapon'].title,
        w_details['weapon'].type.title,
        w_details['weapon'].rarity.title,
        ttl_resources])

    resource_sheet = book.add_worksheet("Resources")
    if ttl_resources == 0:
        resource_sheet.write("A1","No resources required to upgrade weapon",book.add_format({'bold': True}))
    else:
        resource_sheet.write_row("A1",w_details['header_row'],book.add_format({'bold': True}))
        sheet_row = 1
        sheet_col = 0
        # Set default max width for Resource Column
        resource_width = 10
        # write the resources to upgrade weapon
        for row in w_details['data']:
            log.debug(f'sheet_row:{sheet_row}, sheet_col:{sheet_col}, {row}')
            first_i = True
            for i in row:
                if first_i: # this will be text
                    if len(i) > resource_width:
                        resource_width = len(i) + 3
                    resource_sheet.write(sheet_row,sheet_col,i)
                    first_i = False
                else: # Assuming the rest will be numbers. Have to remove comma
                    tmp = i.replace(',','')
                    if tmp.isnumeric():
                        resource_sheet.write(sheet_row,sheet_col,int(tmp))
                    else:
                        resource_sheet.write(sheet_row,sheet_col,i)
                sheet_col +=1
            sheet_col = 0
            sheet_row += 1

        log.debug(f"Setting column A's width to: {resource_width}")
        resource_sheet.set_column("A:A", resource_width)
        resource_sheet.set_column("B:B",13) # Setting Resource ID column width

    book.close()  # close book and save it in "output"
    data_extract.seek(0)  # seek stream on begin to retrieve all data from it

    return send_file(
        data_extract,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'weapon_extract_{id}.xlsx'
    )
