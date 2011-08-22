#     Spreadsheet.py: write simple Excel spreadsheets
#     Copyright (C) University of Manchester 2011 Peter Briggs
#
########################################################################
#
# Spreadsheet.py
#
#########################################################################

"""Spreadsheet

Provides a Spreadsheet class for writing data to an Excel spreadsheet,
using the xlrd, xlwt and xlutils modules.

These can be found at:
http://pypi.python.org/pypi/xlwt/0.7.2
http://pypi.python.org/pypi/xlrd/0.7.1
http://pypi.python.org/pypi/xlutils/1.4.1

xlutils also needs functools:
http://pypi.python.org/pypi/functools

but if you're using Python<2.5 then you need a backported version of
functools, try:
https://github.com/dln/pycassa/blob/90736f8146c1cac8287f66e8c8b64cb80e011513/pycassa/py25_functools.py
"""

#######################################################################
# Import modules that this module depends on
#######################################################################

import xlwt, xlrd
import xlutils, xlutils.copy
from xlwt.Utils import rowcol_to_cell
from xlwt import easyxf

import os
import logging

#######################################################################
# Class definitions
#######################################################################

class Workbook:
    """Class for writing data to an XLS spreadsheet.

    A Workbook represents an XLS spreadsheet, which conists of sheets
    (represented by Worksheet instances).
    """

    def __init__(self,xls_name=''):
        """Create a new Workbook instance.

        If the name of an existing XLS file is specified then the new
        content will be appended to whatever is already in that
        spreadsheet (note that the original spreadsheet will only be
        overwritten if the same name is provided in the 'save' method).
        Otherwise a new (empty) spreadsheet will be created.
        """
        self.name = xls_name
        self.sheets = []
        if not os.path.exists(self.name):
            # New spreadsheet
            self.workbook = xlwt.Workbook()
            if self.name:
                logging.warning("Specified XLS file '%s' not found" %
                                self.name)
        else:
            # Spreadsheet already exists - convert into an xlwt workbook
            rb = xlrd.open_workbook(self.name,formatting_info=True)
            self.workbook = xlutils.copy.copy(rb)
            # Collect the sheets in the workbook
            i = 0
            for s in rb.sheets():
                logging.debug("Adding existing sheet: '%s'" % s.name)
                sheet = self.addSheet(s.name,xlrd_sheet=s,xlrd_index=i)
                i += 1

    def addSheet(self,title,xlrd_sheet=None,xlrd_index=None):
        """Add a new sheet to the spreadsheet.

        Arguments:
          title: title for the sheet
          xlrd_sheet: (optional) an xlrd sheet from an existing XLS
            workbook.
        """
        # Check if a sheet with this name already exists
        logging.debug("Adding sheet '%s'" % title)
        if xlrd_index is None and xlrd_sheet is None:
            try:
                ws = self.getSheet(title)
                logging.warning("Sheet called '%s' already exists" % title)
                return ws
            except KeyError:
                # Not found
                ws = Worksheet(self.workbook,title)
        else:
            # Sheet already exists from original XLS
            ws = Worksheet(self.workbook,title,xlrd_sheet=xlrd_sheet,
                           xlrd_index=xlrd_index)
        self.sheets.append(ws)
        return ws

    def getSheet(self,title):
        """Retrieve a sheet from the spreadsheet.
        """
        for s in self.sheets:
            logging.debug("Searching: sheet '%s'" % s.title)
            if title == s.title: return s
        raise KeyError, "No sheet called '%s' found" % title

    def save(self,xls_name):
        """Finish adding data and write the spreadsheet to disk.
        """
        # Write data for each sheet
        for s in self.sheets:
            s.save()
        # Save workbook
        if os.path.exists(xls_name):
            logging.warning("Overwriting existing file: '%s'" % xls_name)
        self.workbook.save(xls_name)

class Worksheet:
    """Class for writing to a sheet in an XLS spreadsheet.

    A Worksheet object represents a sheet in an XLS spreadsheet.
    """

    def __init__(self,workbook,title,xlrd_index=None,xlrd_sheet=None):
        """Create a new Worksheet instance.
        """
        self.title = title
        self.workbook = workbook
        if xlrd_index is None and xlrd_sheet is None:
            # New worksheet
            self.is_new = True
            self.worksheet = self.workbook.add_sheet(title)
            self.current_row = -1
        else:
            # Existing worksheet
            self.is_new = False
            self.worksheet = self.workbook.get_sheet(xlrd_index)
            self.current_row = xlrd_sheet.nrows - 1
        self.data = []

    def addTabData(self,rows):
        """Write a list of tab-delimited data rows to the sheet.

        Given a list of rows with tab-separated data items,
        write the data to the worksheet.

        Arguments:
          data: Python list representing rows of tab-separated
            data items
        """
        for row in rows:
            self.data.append(row)

    def addText(self,text):
        """Write text to the sheet.
        """
        return self.addTabData(text.split('\n'))

    def insertColumn(self,position,insert_items=None,title=''):
        """Insert a new column into the spreadsheet.
        
        This inserts a new column into each row of data, at the
        specified positional index (starting from 0).

        If insert_item starts with '=' then it's interpreted as a row-wise
        formula. Formulas can be written in the form e.g. "=A+B-C", where
        the letters indicate columns in the final XLS spreadsheet. When the
        formulae are written they are expanded to include the row number
        e.g. "=A1+B1-C1", "A2+B2-C2" etc.

        Note: at present columns can only be inserted into new sheets.

        Arguments:
          position: positional index for the column to be inserted
            at (0=A, 1=B etc)
          title: (optional) value to be written to the first row (i.e. a column
            title)
          insert_items: value(s) to be inserted; either a single item, or a
            list of items. Each item can be blank, a constant value, or a
            formula.
        """
        if not self.is_new:
            logging.error("ERROR cannot insert data into pre-existing worksheet")
            return False
        insert_title = True
        # Loop over rows
        for i in range(len(self.data)):
            row = self.data[i]
            items = row.split('\t')
            new_items = []
            for j in range(len(items)):
                # Insert appropriate item at this position
                if j == position:
                    if insert_title:
                        # Title for new column
                        new_items.append(title)
                        insert_title = False
                    else:
                        # Data item
                        if isinstance(insert_items,list):
                            try:
                                insert_item = insert_items[j-1]
                            except IndexError:
                                # Ran out of items?
                                insert_item = ''
                        else:
                            insert_item = insert_items
                        new_items.append(insert_item)
                # Append the existing row data
                new_items.append(items[j])
            # Replace old row with new one
            self.data[i] = '\t'.join(new_items)
        # Finished successfully
        return True

    def getColumnId(self,name):
        """Lookup XLS column id from name of column.

        If there is no data, or if the name isn't in the header
        row of the data, then an exception is raised.

        Returns the column identifier (i.e. 'A', 'B' etc) for the
        column with the matching name.
        """
        try:
            i = self.data[0].split('\t').index(name)
            return string.uppercase[i]
        except IndexError:
            # Column name not found
            raise IndexError, "Column '%s' not found" % name

    def save(self):
        """Write the new data to the spreadsheet.
        """
        for row in self.data:
            self.current_row += 1
            cindex = 0
            for item in row.split('\t'):
                if str(item).startswith('='):
                    # Formula item
                    formula = ''
                    for c in item[1:]:
                        formula += c
                        if c.isalpha() and c.isupper:
                            # Add the row number afterwards
                            # NB xlwt takes row numbers from zero,
                            # while XLS starts from 1
                            formula += str(self.current_row+1)
                    self.worksheet.write(self.current_row,cindex,
                                         xlwt.Formula(formula))
                else:
                    # Data item
                    self.worksheet.write(self.current_row,cindex,item)
                cindex += 1
        # Update/reset the sheet properties etc
        self.data = []
        self.is_new = False
        # Finished
        return

class Spreadsheet:
    """Class for creating and writing a spreadsheet.

    This creates a very simple single-sheet workbook.
    """

    def __init__(self,name,title):
        """Create a new Spreadsheet instance.

        If the named spreadsheet already exists then any new
        data is appended to the it.

        Arguments:
          name: name of the XLS format spreadsheet to be created. 
          title: title for the new sheet.
        """
        self.workbook = xlwt.Workbook()
        self.name = name
        self.headers = []
        if not os.path.exists(self.name):
            # New spreadsheet
            self.sheet = self.workbook.add_sheet(title)
            self.current_row = -1
        else:
            # Already exists - convert into an xlwt workbook
            rb = xlrd.open_workbook(self.name,formatting_info=True)
            rs = rb.sheet_by_index(0)
            self.workbook = xlutils.copy.copy(rb)
            self.sheet = self.workbook.get_sheet(0)
            # Get some info on the sheet
            self.current_row = rs.nrows
            # Assume that the first row with data is the header
            # and collect the titles
            for rindex in range(rs.nrows):
                if str(rs.cell(rindex,0).value) != '':
                    for cindex in range(rs.ncols):
                        self.headers.append(rs.cell(rindex,cindex).value)
                    break

    def addTitleRow(self,headers):
        """Add a title row to the spreadsheet.

        The title row will have the font style set to bold for all
        cells.

        Arguments:
          headers: list of titles to be added.

        Returns:
          Integer index of row just written
        """
        self.headers = headers
        self.current_row += 1
        cindex = 0
        # Add the header row in bold font
        return self.addRow(self.headers,
                           bold=True,
                           set_widths=True)

    def addEmptyRow(self,color=None):
        """Add an empty row to the spreadsheet.

        Inserts an empty row into the next position in the
        spreadsheet.

        Arguments:
          color: optional background color for the empty row

        Returns:
          Integer index of (empty) row just written
        """
        if not color:
            self.current_row += 1
            return self.current_row
        else:
            row = []
            for item in self.headers:
                row.append('')
            return self.addRow(row,bg_color=color)

    def addRow(self,data,set_widths=False,bold=False,wrap=False,bg_color=''):
        """Add a row of data to the spreadsheet.

        Arguments:
          data: list of data items to be added.

          set_widths: (optional) Boolean; if True then set the column
            width to the length of the cell contents for each cell
            in the new row

          bold: (optional) use bold font for cells

          wrap: (optional) wrap the cell content

          bg_color: (optional) set the background color for the cell

        Returns:
          Integer index of row just written
        """
        # Set up style attributes
        style = {'font': [],
                 'alignment': [],
                 'pattern': []}
        if bold:
            style['font'].append('bold True');
        if wrap:
            style['alignment'].append('wrap True')
        if bg_color:
            style['pattern'].append('pattern solid')
            style['pattern'].append('fore_color %s' % bg_color)
        # Build easyfx object to apply styles
        easyxf_style = ''
        for key in style.keys():
            if style[key]:
                easyxf_style += '%s: ' % key
                easyxf_style += ', '.join(style[key])
                easyxf_style += '; '
        xf_style = easyxf(easyxf_style)
        # Write the row
        self.current_row += 1
        cindex = 0
        for item in data:
            if str(item).startswith('='):
                # Formula
                print "Formulae not implemented"
                # Formula example code
                #
                #sheet.write(2,3,xlwt.Formula('%s/%s*100' %
                #                  (rowcol_to_cell(2,2),rowcol_to_cell(2,1))))
                #
                self.sheet.write(self.current_row,cindex_item,xf_style)
            else:
                # Data
                self.sheet.write(self.current_row,cindex,item,xf_style)
            if set_widths:
                # Set the column width to match the cell contents
                self.sheet.col(cindex).width = 256*(len(item)+5)
            cindex += 1
        return self.current_row

    def write(self):
        """Write the spreadsheet to file.
        """
        self.workbook.save(self.name)

#######################################################################
# Main program
#######################################################################

if __name__ == "__main__":
    # Example writing XLS with Spreadsheet class
    wb = Spreadsheet('test.xls','test')
    wb.addTitleRow(['File','Total reads','Unmapped reads'])
    wb.addEmptyRow()
    wb.addRow(['DR_1',875897,713425])
    wb.write()
    # Example writing new XLS with Workbook class
    wb = Workbook()
    ws = wb.addSheet('test1')
    ws.addText("Hello\tGoodbye\nGoodbye\tHello")
    wb.save('test2.xls')
    # Example appending to existing XLS with Workbook class
    wb = Workbook('test2.xls')
    ws = wb.getSheet('test1')
    ws.addText("Some more data for you")
    ws = wb.addSheet('test2')
    ws.addText("Hahahah")
    wb.save('test3.xls')

