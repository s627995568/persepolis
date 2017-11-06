# -*- coding: utf-8 -*-
"""
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sqlite3
import ast
import os
import platform
from time import sleep
import random
import traceback
# get home address for this user
home_address = os.path.expanduser("~")

# find os platform
os_type = platform.system()



# download manager config folder .
if os_type == 'Linux' or os_type == 'FreeBSD' or os_type == 'OpenBSD':
    config_folder = os.path.join(
        str(home_address), ".config/persepolis_download_manager")
elif os_type == 'Darwin':
    config_folder = os.path.join(
        str(home_address), "Library/Application Support/persepolis_download_manager")
elif os_type == 'Windows':
    config_folder = os.path.join(
        str(home_address), 'AppData', 'Local', 'persepolis_download_manager')

# persepolis tmp folder path
if os_type != 'Windows':
    user_name_split = home_address.split('/')
    user_name = user_name_split[2]
    persepolis_tmp = '/tmp/persepolis_' + user_name
else:
    persepolis_tmp = os.path.join(
        str(home_address), 'AppData', 'Local', 'persepolis_tmp')



# This class manages TempDB
# TempDB contains gid of active downloads in every session.
class TempDB():
    def __init__(self):
        # temp_db saves in RAM
        # temp_db_connection

        self.temp_db_connection = sqlite3.connect(':memory:', check_same_thread=False)

        # temp_db_cursor
        self.temp_db_cursor = self.temp_db_connection.cursor()
        self.lock = False

    def lockCursor(self):
        while self.lock:
            rand_float = random.uniform(0, 0.5)
            sleep(rand_float)
        
        self.lock = True


    # temp_db_table contains gid of active downloads. 
    def createTables(self):
        self.lockCursor()
        self.temp_db_cursor.execute("""CREATE TABLE IF NOT EXISTS temp_db_table(
                                                                                ID INTEGER PRIMARY KEY,
                                                                                gid TEXT
                                                                                )""") 
        self.temp_db_connection.commit()
        self.lock = False

    # insert new item in temp_db_table
    def insertInTempTable(self, gid):
        self.lockCursor()
        self.temp_db_cursor.execute("""INSERT INTO temp_db_table VALUES(
                                                                NULL,
                                                                '{}')""".format(gid)) 

        self.temp_db_connection.commit()
        self.lock = False

    def deleteGidFromTempTable(self, gid):
        self.lockCursor()
        self.temp_db_cursor.execute("""DELETE FROM temp_db_table WHERE gid = '{}'""".format(gid))

        self.temp_db_connection.commit()

        self.lock = False

    def returnGids(self):
        self.lockCursor()
        self.temp_db_cursor.execute("""SELECT gid FROM temp_db_table""")
        
        list = self.temp_db_cursor.fetchall()

        self.lock = False
        gid_list = []

        for tuple in list:
            gid = tuple[0]
            gid_list.append(gid)
            

        return gid_list


    # close connections
    def closeConnections(self):
        self.lockCursor()
        self.temp_db_cursor.close()
        self.temp_db_connection.close()
        self.lock = False




# plugins.db is store links, when browser plugins are send new links.
# This class is managing plugin.db   
class PluginsDB():
    def __init__(self):
        # plugins.db file path
        plugins_db_path = os.path.join(persepolis_tmp, 'plugins.db')

        # plugins_db_connection
        self.plugins_db_connection = sqlite3.connect(plugins_db_path)

        # plugins_db_cursor
        self.plugins_db_cursor = self.plugins_db_connection.cursor()

    # plugins_db_table contains links that sends by browser plugins. 
    def createTables(self):
        self.plugins_db_cursor.execute("""CREATE TABLE IF NOT EXISTS plugins_db_table(
                                                                                ID INTEGER PRIMARY KEY,
                                                                                link TEXT,
                                                                                referer TEXT,
                                                                                load_cookies TEXT,
                                                                                user_agent TEXT,
                                                                                header TEXT,
                                                                                out TEXT,
                                                                                status TEXT
                                                                                )""") 
        self.plugins_db_connection.commit()

    # insert new item in plugins_db_table
    def insertInPluginsTable(self, dict):
        self.plugins_db_cursor.execute("""INSERT INTO plugins_db_table VALUES(
                                                                    NULL,
                                                                    :link,
                                                                    :referer,
                                                                    :load_cookies,
                                                                    :user_agent,
                                                                    :header,
                                                                    :out,
                                                                    'new'
                                                                        )""", dict)

        self.plugins_db_connection.commit()

# this method returns all new links in plugins_db_table
    def returnNewLinks(self):
        self.plugins_db_cursor.execute("""SELECT link, referer, load_cookies, user_agent, header, out
                                            FROM plugins_db_table
                                            WHERE status = 'new'""")

        list = self.plugins_db_cursor.fetchall()

        # chang all rows status to 'old'
        self.plugins_db_cursor.execute("""UPDATE plugins_db_table SET status = 'old'
                                            WHERE status = 'new'""")

        # commit changes
        self.plugins_db_connection.commit()

        # create new_list
        new_list = []

        # put the information in tuples in dictionary format and add it to new_list
        for tuple in list:
            print(tuple)
            dict = {'link': tuple[0],
                    'referer': tuple[1],
                    'load_cookies': tuple[2],
                    'user_agent': tuple[3],
                    'header': tuple[4],
                    'out': tuple[5]
                    }

            new_list.append(dict)

        # return results in list format!
        # every member of this list is a dictionary.
        # every dictionary contains download information
        return new_list

    # delete old links from data base
    def deleteOldLinks(self):
        self.plugins_db_cursor.execute("""DELETE FROM plugins_db_table WHERE status = 'old'""")
        # commit changes
        self.plugins_db_connection.commit()



    # close connections
    def closeConnections(self):
        self.plugins_db_cursor.close()
        self.plugins_db_connection.close()

# persepolis main data base contains downloads information
# This class is managing persepolis.db 
class PersepolisDB():
    def __init__(self):
        # persepolis.db file path 
        persepolis_db_path = os.path.join(config_folder, 'persepolis.db')

        # persepolis_db_connection
        self.persepolis_db_connection = sqlite3.connect(persepolis_db_path, check_same_thread=False)

        # turn FOREIGN KEY Support on!
        self.persepolis_db_connection.execute('pragma foreign_keys=ON')

        # persepolis_db_cursor
        self.persepolis_db_cursor = self.persepolis_db_connection.cursor()

        self.lock = False

    def lockCursor(self):
        while self.lock:
            rand_float = random.uniform(0, 0.5)
            sleep(rand_float)

#         print(traceback.extract_stack(None, 2)[0][2])
        self.lock = True


    def createTables(self):
    # queues_list contains name of categories and category settings
        try:

            self.lockCursor()
            # Create category_db_table and add 'All Downloads' and 'Single Downloads' to it
            self.persepolis_db_cursor.execute("""CREATE TABLE category_db_table(
                                                                category TEXT PRIMARY KEY,
                                                                start_time_enable TEXT,
                                                                start_time TEXT,
                                                                end_time_enable TEXT,
                                                                end_time TEXT,
                                                                reverse TEXT,
                                                                limit_enable TEXT,
                                                                limit_value TEXT,
                                                                after_download TEXT,
                                                                gid_list TEXT
                                                                            )""")

            self.persepolis_db_connection.commit()
            
            # job is done! open the lock
            self.lock = False



            all_downloads_dict = {'category': 'All Downloads',
                    'start_time_enable': 'no',
                    'start_time': '0:0',
                    'end_time_enable': 'no',
                    'end_time': '0:0',
                    'reverse': 'no',
                    'limit_enable': 'no',
                    'limit_value': '0K',
                    'after_download': 'no',
                    'gid_list': '[]'
                    }

            single_downloads_dict = {'category': 'Single Downloads',
                    'start_time_enable': 'no',
                    'start_time': '0:0',
                    'end_time_enable': 'no',
                    'end_time': '0:0',
                    'reverse': 'no',
                    'limit_enable': 'no',
                    'limit_value': '0K',
                    'after_download': 'no',
                    'gid_list': '[]'
                    }



            self.insertInCategoryTable(all_downloads_dict)
            self.insertInCategoryTable(single_downloads_dict)
        except Exception as e:
            self.lock = False

            print(e)

            self.lockCursor()

    # download table contains download table download items information
        self.persepolis_db_cursor.execute("""CREATE TABLE IF NOT EXISTS download_db_table(
                                                                                    file_name TEXT,
                                                                                    status TEXT,
                                                                                    size TEXT,
                                                                                    downloaded_size TEXT,
                                                                                    percent TEXT,
                                                                                    connections TEXT,
                                                                                    rate TEXT,
                                                                                    estimate_time_left TEXT,
                                                                                    gid TEXT PRIMARY KEY,
                                                                                    link TEXT,
                                                                                    first_try_date TEXT,
                                                                                    last_try_date TEXT,
                                                                                    category TEXT,
                                                                                    FOREIGN KEY(category) REFERENCES category_db_table(category)
                                                                                    ON UPDATE CASCADE
                                                                                    ON DELETE CASCADE
                                                                                         )""")


    # addlink_db_table contains addlink window download information
        self.persepolis_db_cursor.execute("""CREATE TABLE IF NOT EXISTS addlink_db_table(
                                                                                ID INTEGER PRIMARY KEY,
                                                                                gid TEXT,
                                                                                out TEXT,
                                                                                start_time TEXT,
                                                                                end_time TEXT,
                                                                                link TEXT,
                                                                                ip TEXT,
                                                                                port TEXT,
                                                                                proxy_user TEXT,
                                                                                proxy_passwd TEXT,
                                                                                download_user TEXT,
                                                                                download_passwd TEXT,
                                                                                connections TEXT,
                                                                                limit_value TEXT,
                                                                                download_path TEXT,
                                                                                referer TEXT,
                                                                                load_cookies TEXT,
                                                                                user_agent TEXT,
                                                                                header TEXT,
                                                                                after_download TEXT,
                                                                                FOREIGN KEY(gid) REFERENCES download_db_table(gid) 
                                                                                ON UPDATE CASCADE 
                                                                                ON DELETE CASCADE 
                                                                                    )""") 
        self.persepolis_db_connection.commit()

        # job is done! open the lock
        self.lock = False




    # insert new category in category_db_table
    def insertInCategoryTable(self, dict):    
        self.lockCursor()

        self.persepolis_db_cursor.execute("""INSERT INTO category_db_table VALUES(
                                                                            :category,
                                                                            :start_time_enable,
                                                                            :start_time,
                                                                            :end_time_enable,
                                                                            :end_time,
                                                                            :reverse,
                                                                            :limit_enable,
                                                                            :limit_value,
                                                                            :after_download,
                                                                            :gid_list
                                                                            )""", dict)
        self.persepolis_db_connection.commit()
 
        # job is done! open the lock
        self.lock = False





    # insert in to download_db_table in persepolis.db
    def insertInDownloadTable(self, dict):
        self.lockCursor()

        self.persepolis_db_cursor.execute("""INSERT INTO download_db_table VALUES(
                                                                            :file_name,
                                                                            :status,
                                                                            :size,
                                                                            :downloaded_size,
                                                                            :percent,
                                                                            :connections,
                                                                            :rate,
                                                                            :estimate_time_left,
                                                                            :gid,
                                                                            :link,
                                                                            :first_try_date,
                                                                            :last_try_date,
                                                                            :category
                                                                            )""", dict)

        # commit changes
        self.persepolis_db_connection.commit()


        # job is done! open the lock
        self.lock = False




        # item must be inserted to gid_list of 'All Downloads' and gid_list of category
        # find download category and gid
        category = dict['category']
        gid = dict['gid']
         
        for category_item in 'All Downloads', category:
            
            # get category_dict from data base
            category_dict = self.searchCategoryInCategoryTable(category_item)

            # get gid_list
            gid_list = category_dict['gid_list']

            # add gid of item to gid_list
            gid_list = gid_list.append(gid)

            # updata category_db_table
            self.updateCategoryTable([category_dict])


    # insert in addlink table in persepolis.db 
    def insertInAddLinkTable(self, dict):
        self.lockCursor()


        # first column and after download column is NULL
        self.persepolis_db_cursor.execute("""INSERT INTO addlink_db_table VALUES(NULL,
                                                                                :gid,
                                                                                :out,
                                                                                :start_time,
                                                                                :end_time,
                                                                                :link,
                                                                                :ip,
                                                                                :port,
                                                                                :proxy_user,
                                                                                :proxy_passwd,
                                                                                :download_user,
                                                                                :download_passwd,
                                                                                :connections,
                                                                                :limit_value,
                                                                                :download_path,
                                                                                :referer,
                                                                                :load_cookies,
                                                                                :user_agent,
                                                                                :header,
                                                                                NULL
                                                                                )""", dict)
        self.persepolis_db_connection.commit() 
    
 
        # job is done! open the lock
        self.lock = False





    # return download information in download_db_table with special gid.
    def searchGidInDownloadTable(self, gid):
        self.lockCursor()

        self.persepolis_db_cursor.execute("""SELECT * FROM download_db_table WHERE gid = '{}'""".format(str(gid)))
        list = self.persepolis_db_cursor.fetchall()

        # job is done! open the lock
        self.lock = False




        if list:
            tuple = list[0]
        else:
            return None

        dict = {'file_name': tuple[0],
                'status': tuple[1],
                'size': tuple[2],
                'downloaded_size': tuple[3],
                'percent': tuple[4],
                'connections': tuple[5],
                'rate': tuple[6],
                'estimate_time_left': tuple[7],
                'gid': tuple[8],
                'link': tuple[9],
                'first_try_date': tuple[10],
                'last_try_date': tuple[11],
                'category': tuple[12]
                }

        # return results
        return dict

    # return all items in download_db_table
    # '*' for category, cause that method returns all items. 
    def returnItemsInDownloadTable(self, category=None):
        self.lockCursor()

        if category:
            self.persepolis_db_cursor.execute("""SELECT * FROM download_db_table WHERE category = '{}'""".format(category))
        else:
            self.persepolis_db_cursor.execute("""SELECT * FROM download_db_table""")

        rows = self.persepolis_db_cursor.fetchall()

        # job is done! open the lock
        self.lock = False




        downloads_dict = {}
        for tuple in rows:
            # change format of tuple to dictionary
            dict = {'file_name': tuple[0],
                    'status': tuple[1],
                    'size': tuple[2],
                    'downloaded_size': tuple[3],
                    'percent': tuple[4],
                    'connections': tuple[5],
                    'rate': tuple[6],
                    'estimate_time_left': tuple[7],
                    'gid': tuple[8],
                    'link': tuple[9],
                    'first_try_date': tuple[10],
                    'last_try_date': tuple[11],
                    'category': tuple[12]
                    }

            # add dict to the downloads_dict
            # gid is key and dict is value
            downloads_dict[tuple[8]] = dict


        return downloads_dict

      

    # return download information in addlink_db_table with special gid.
    def searchGidInAddLinkTable(self, gid):
        self.lockCursor()

        self.persepolis_db_cursor.execute("""SELECT * FROM addlink_db_table WHERE gid = '{}'""".format(str(gid)))
        list = self.persepolis_db_cursor.fetchall()

        # job is done! open the lock
        self.lock = False




        if list:
            tuple = list[0]
        else:
            return None

        dict = {'gid' :tuple[1],
                'out': tuple[2],
                'start_time': tuple[3],
                'end_time': tuple[4],
                'link': tuple[5],
                'ip': tuple[6],
                'port': tuple[7],
                'proxy_user': tuple[8],
                'proxy_passwd': tuple[9],
                'download_user': tuple[10],
                'download_passwd': tuple[11],
                'connections': tuple[12],
                'limit_value': tuple[13],
                'download_path' : tuple[14],
                'referer': tuple[15],
                'load_cookies': tuple[16],
                'user_agent': tuple[17],
                'header': tuple[18],
                'after_download': tuple[19]
                }

        return dict


    # return items in addlink_db_table
    # '*' for category, cause that method returns all items. 
    def returnItemsInAddLinkTable(self, category=None):
        self.lockCursor()

        if category:
            self.persepolis_db_cursor.execute("""SELECT * FROM addlink_db_table WHERE category = '{}'""".format(category))
        else:
            self.persepolis_db_cursor.execute("""SELECT * FROM addlink_db_table""")

        rows = self.persepolis_db_cursor.fetchall()

        # job is done! open the lock
        self.lock = False




        addlink_dict = {}
        for tuple in rows:
            # change format of tuple to dictionary
            dict = {'gid' :tuple[1],
                    'out': tuple[2],
                    'start_time': tuple[3],
                    'end_time': tuple[4],
                    'link': tuple[5],
                    'ip': tuple[6],
                    'port': tuple[7],
                    'proxy_user': tuple[8],
                    'proxy_passwd': tuple[9],
                    'download_user': tuple[10],
                    'download_passwd': tuple[11],
                    'connections': tuple[12],
                    'limit_value': tuple[13],
                    'download_path' : tuple[13],
                    'referer': tuple[14],
                    'load_cookies': tuple[15],
                    'user_agent': tuple[16],
                    'header': tuple[17],
                    'after_download': tuple[18]
                    }

            # add dict to the addlink_dict
            # gid as key and dict as value
            addlink_dict[tuple[1]] = dict


        return addlink_dict

 

# this method updates download_db_table
    def updateDownloadTable(self, list):
        self.lockCursor()

        keys_list = ['file_name',
                    'status',
                    'size',
                    'downloaded_size',
                    'percent',
                    'connections',
                    'rate',
                    'estimate_time_left',
                    'gid',
                    'link',
                    'first_try_date',
                    'last_try_date',
                    'category'
                    ]

        for dict in list:
            for key in keys_list:
                # if a key is missed in dict, 
                # then add this key to the dict and assign None value for the key. 
                if key not in dict.keys():
                    dict[key] = None

            # update data base if value for the keys is not None
            self.persepolis_db_cursor.execute("""UPDATE download_db_table SET   file_name = coalesce(:file_name, file_name),
                                                                                    status = coalesce(:status, status),
                                                                                    size = coalesce(:size, size),
                                                                                    downloaded_size = coalesce(:downloaded_size, downloaded_size),
                                                                                    percent = coalesce(:percent, percent),
                                                                                    connections = coalesce(:connections, connections),
                                                                                    rate = coalesce(:rate, rate),
                                                                                    estimate_time_left = coalesce(:estimate_time_left, estimate_time_left),
                                                                                    link = coalesce(:link, link),
                                                                                    first_try_date = coalesce(:first_try_date, first_try_date),
                                                                                    last_try_date = coalesce(:last_try_date, last_try_date),
                                                                                    category = coalesce(:category, category)
                                                                                    WHERE gid = :gid""", dict)

        # commit the changes
        self.persepolis_db_connection.commit()


        # job is done! open the lock
        self.lock = False




# this method updates category_db_table
    def updateCategoryTable(self, list):
        self.lockCursor()

        keys_list = ['category',
                    'start_time_enable',
                    'start_time',
                    'end_time_enable',
                    'end_time',
                    'reverse',
                    'limit_enable',
                    'limit_value',
                    'after_download',
                    'gid_list']

        for dict in list:

            # format of gid_list is list and must be converted to string for sqlite3
            if 'gid_list' in dict.keys():
                dict['gid_list'] = str(dict['gid_list'])

            for key in keys_list:
                # if a key is missed in dict, 
                # then add this key to the dict and assign None value for the key. 
                if key not in dict.keys():
                    dict[key] = None




            # update data base if value for the keys is not None
            self.persepolis_db_cursor.execute("""UPDATE category_db_table SET   start_time_enable = coalesce(:start_time_enable, start_time_enable),
                                                                                    start_time = coalesce(:start_time, start_time),
                                                                                    end_time_enable = coalesce(:end_time_enable, end_time_enable),
                                                                                    end_time = coalesce(:end_time, end_time),
                                                                                    reverse = coalesce(:reverse, reverse),
                                                                                    limit_enable = coalesce(:limit_enable, limit_enable),
                                                                                    limit_value = coalesce(:limit_value, limit_value),
                                                                                    after_download = coalesce(:after_download, after_download),
                                                                                    gid_list = coalesce(:gid_list, gid_list)
                                                                                    WHERE category = :category""", dict)

        # commit changes
        self.persepolis_db_connection.commit()


        # job is done! open the lock
        self.lock = False




# this method updates addlink_db_table
    def updateAddLinkTable(self, list):

        self.lockCursor()

        keys_list = ['gid',
                    'out',
                    'start_time',
                    'end_time',
                    'link',
                    'ip',
                    'port',
                    'proxy_user',
                    'proxy_passwd',
                    'download_user',
                    'download_passwd',
                    'connections',
                    'limit_value',
                    'download_path',
                    'referer',
                    'load_cookies',
                    'user_agent',
                    'header',
                    'after_download']

        for dict in list:
            for key in keys_list:  
                # if a key is missed in dict, 
                # then add this key to the dict and assign None value for the key. 
                if key not in dict.keys():
                    dict[key] = None 

            # update data base if value for the keys is not None
            self.persepolis_db_cursor.execute("""UPDATE addlink_db_table SET out = coalesce(:out, out),
                                                                                start_time = coalesce(:start_time, start_time),
                                                                                end_time = coalesce(:end_time, end_time),
                                                                                link = coalesce(:link, link),
                                                                                ip = coalesce(:ip, ip),
                                                                                port = coalesce(:port, port),
                                                                                proxy_user = coalesce(:proxy_user, proxy_user),
                                                                                proxy_passwd = coalesce(:proxy_passwd, proxy_passwd),
                                                                                download_user = coalesce(:download_user, download_user),
                                                                                download_passwd = coalesce(:download_passwd, download_passwd),
                                                                                connections = coalesce(:connections, connections),
                                                                                limit_value = coalesce(:limit_value, limit_value),
                                                                                download_path = coalesce(:download_path, download_path),
                                                                                referer = coalesce(:referer, referer),
                                                                                load_cookies = coalesce(:load_cookies, load_cookies),
                                                                                user_agent = coalesce(:user_agent, user_agent),
                                                                                header = coalesce(:header, header),
                                                                                after_download = coalesce(:after_download , after_download)
                                                                                WHERE gid = :gid""", dict)
        # commit the changes!
        self.persepolis_db_connection.commit() 


        # job is done! open the lock
        self.lock = False




    
    def setDefaultGidInAddlinkTable(self, gid, start_time=False, end_time=False, after_download=False):
        self.lockCursor()

        # change value of start_time and end_time and after_download for special gid to NULL value
        if start_time:
            self.persepolis_db_cursor.execute("""UPDATE addlink_db_table SET start_time = NULL
                                                                        WHERE gid = '{}' """.format(gid))
        if end_time:
            self.persepolis_db_cursor.execute("""UPDATE addlink_db_table SET end_time = NULL
                                                                        WHERE gid = '{}' """.format(gid))
        if after_download:
            self.persepolis_db_cursor.execute("""UPDATE addlink_db_table SET after_download = NULL
                                                                        WHERE gid = '{}' """.format(gid))
 
        self.persepolis_db_connection.commit()


        # job is done! open the lock
        self.lock = False





    # return category information in category_db_table
    def searchCategoryInCategoryTable(self, category):
        self.lockCursor()

        self.persepolis_db_cursor.execute("""SELECT * FROM category_db_table WHERE category = '{}'""".format(str(category)))
        list = self.persepolis_db_cursor.fetchall()


        # job is done! open the lock
        self.lock = False





        if list:
            tuple = list[0]
        else:
            return None


        # convert string to list
        gid_list = ast.literal_eval(tuple[9]) 


        # create a dictionary from results
        dict = {'category': tuple[0],
                'start_time_enable': tuple[1],
                'start_time': tuple[2],
                'end_time_enable': tuple[3],
                'end_time': tuple[4],
                'reverse': tuple[5],
                'limit_enable': tuple[6],
                'limit_value': tuple[7],
                'after_download': tuple[8],
                'gid_list': gid_list 
                }

        # return dictionary
        return dict

    # return categories name 
    def categoriesList(self):
        self.lockCursor()

        self.persepolis_db_cursor.execute("""SELECT category FROM category_db_table ORDER BY ROWID""")
        rows = self.persepolis_db_cursor.fetchall() 

        # create a list from categories name
        queues_list = []

        for tuple in rows:
            queues_list.append(tuple[0])

        # job is done! open the lock
        self.lock = False




        # return the list
        return queues_list



    def setDBTablesToDefaultValue(self):
        self.lockCursor()

    # change start_time_enable , end_time_enable , reverse ,
    # limit_enable , after_download value to default value !
        self.persepolis_db_cursor.execute("""UPDATE category_db_table SET start_time_enable = 'no', end_time_enable = 'no',
                                        reverse = 'no', limit_enable = 'no', after_download = 'no'""")

    # change status of download to 'stopped' if status isn't 'complete' or 'error'
        self.persepolis_db_cursor.execute("""UPDATE download_db_table SET status = 'stopped' 
                                        WHERE status NOT IN ('complete', 'error')""")

    # change start_time and end_time and
    # after_download value to None in addlink_db_table!
        self.persepolis_db_cursor.execute("""UPDATE addlink_db_table SET start_time = NULL,
                                                                        end_time = NULL,
                                                                        after_download = NULL
                                                                                        """)
    
        self.persepolis_db_connection.commit()


        # job is done! open the lock
        self.lock = False



    def findActiveDownloads(self, category=None):
        self.lockCursor()

        # find download items is download_db_table with status = "downloading" or "waiting" or paused or scheduled
        if category:
            self.persepolis_db_cursor.execute("""SELECT gid FROM download_db_table WHERE (category = '{}') AND (status = 'downloading' OR status = 'waiting' 
                                            OR status = 'scheduled' OR status = 'paused')""".format(str(category)))
        else:
            self.persepolis_db_cursor.execute("""SELECT gid FROM download_db_table WHERE (status = 'downloading' OR status = 'waiting' 
                                            OR status = 'scheduled' OR status = 'paused')""")


        # create a list for returning answer
        list = self.persepolis_db_cursor.fetchall()
        gid_list = []

        for tuple in list:
            gid_list.append(tuple[0])
            
        # job is done! open the lock
        self.lock = False


        return  gid_list 

# This method deletes a category from category_db_table
    def deleteCategory(self, category):

        # delete gids of this category from gid_list of 'All Downloads'
        category_dict = self.searchCategoryInCategoryTable(category)
        all_downloads_dict = self.searchCategoryInCategoryTable('All Downloads')

        # get gid_list
        category_gid_list = category_dict['gid_list']
        all_downloads_gid_list = all_downloads_dict['gid_list']

        for gid in category_gid_list:
            # delete item from all_downloads_gid_list
            all_downloads_gid_list.remove(gid)

        # update category_db_table
        self.updateCategoryTable([all_downloads_dict])

        # delete category from data_base
        self.lockCursor()

        self.persepolis_db_cursor.execute("""DELETE FROM category_db_table WHERE category = '{}'""".format(str(category)))

        # commit changes
        self.persepolis_db_connection.commit()

        # job is done! open the lock
        self.lock = False




# This method deletes a download item from download_db_table
    def deleteItemInDownloadTable(self, gid, category):
        self.lockCursor()

        self.persepolis_db_cursor.execute("""DELETE FROM download_db_table WHERE gid = '{}'""".format(str(gid)))

        # commit changes
        self.persepolis_db_connection.commit()

        # job is done! open the lock
        self.lock = False



        # delete item from gid_list in category and All Downloads
        for category_name in category, 'All Downloads':
            category_dict = self.searchCategoryInCategoryTable(category_name)

            # get gid_list
            gid_list = category_dict['gid_list']

            # delete item
            gid_list.remove(gid)

            # update category_db_table
            self.updateCategoryTable([category_dict])

    # close connections
    def closeConnections(self):
        self.lockCursor()

        self.persepolis_db_cursor.close()
        self.persepolis_db_connection.close()

        # job is done! open the lock
        self.lock = False












