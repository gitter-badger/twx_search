import io
import json
import xml.etree.ElementTree as ET
import zipfile
from queue import Queue
from threading import Thread

from flask import Flask, render_template
from flask import request
from whoosh.fields import SchemaClass, TEXT, ID, BOOLEAN
from whoosh.filedb.filestore import FileStorage
from whoosh.qparser import QueryParser
from whoosh.writing import AsyncWriter

import config as config

app = Flask(__name__)

storage = FileStorage(config.INDEX_DIR_PATH)

PROJECT_NAME = 'project_name'
PROJECT_ID = 'project_id'
SNAPSHOT_NAME = 'snapshot_name'
SNAPSHOT_ID = 'snapshot_id'
BRANCH_NAME = 'branch_name'
BRANCH_ID = 'branch_id'
ITEM_NAME = 'item_name'
ITEM_ID = 'item_id'
ITEM_TYPE = 'item_type'
ITEM_CONTENT = 'item_content'
IS_TOOLKIT = 'is_toolkit'
TOOLKIT_PROJECT_NAME = 'toolkit_project_name'
TOOLKIT_PROJECT_ID = 'toolkit_project_id'
TOOLKIT_SNAPSHOT_NAME = 'toolkit_snapshot_name'
TOOLKIT_SNAPSHOT_ID = 'toolkit_snapshot_id'
TOOLKIT_BRANCH_NAME = 'toolkit_branch_name'
TOOLKIT_BRANCH_ID = 'toolkit_branch_id'


class Mydocument(SchemaClass):
    project_name = ID(stored=True)
    project_id = ID(stored=True)
    snapshot_name = ID(stored=True)
    snapshot_id = ID(stored=True)
    branch_name = ID(stored=True)
    branch_id = ID(stored=True)
    item_name = ID(stored=True)
    item_id = ID(stored=True)
    item_type = ID(stored=True)
    item_content = TEXT(stored=True)
    is_toolkit = BOOLEAN(stored=True)
    toolkit_project_name = ID(stored=True)
    toolkit_project_id = ID(stored=True)
    toolkit_snapshot_name = ID(stored=True)
    toolkit_snapshot_id = ID(stored=True)
    toolkit_branch_name = ID(stored=True)
    toolkit_branch_id = ID(stored=True)
    apppath = ID(stored=True)


def get_meta_info(packagexml):
    meta_info = {}
    project_elem = packagexml.find('./target/project')
    meta_info[PROJECT_NAME] = project_elem.attrib['name']
    meta_info[PROJECT_ID] = project_elem.attrib['id']

    snapshot_elem = packagexml.find('./target/snapshot')
    meta_info[SNAPSHOT_NAME] = snapshot_elem.attrib['name']
    meta_info[SNAPSHOT_ID] = snapshot_elem.attrib['id']

    branch_elem = packagexml.find('./target/branch')
    meta_info[BRANCH_NAME] = branch_elem.attrib['name']
    meta_info[BRANCH_ID] = branch_elem.attrib['id']

    return meta_info


def store_all_items(ix, zf, app_meta_info, tookit_meta_info, itemsxmlnode):
    for object in itemsxmlnode:
        filename = 'objects/' + object.attrib['id'] + '.xml'
        content = zf.read(filename)
        itemxml = ET.fromstring(content).findall('./')[0]
        if itemxml.tag.lower() != 'smartfolder':
            if itemxml.tag == 'managedAsset' and itemxml.attrib['name'].endswith('.js'):
                managedAssetId = itemxml.find('./managedAssetId').text
                assetUuid = itemxml.find('./assetUuid').text
                content = zf.read('files/' + managedAssetId + '/' + assetUuid)
            try:
                content = content.decode('utf-8')
            except:
                print("erroe")
                content = u"error"
            item = {}
            item[ITEM_NAME] = itemxml.attrib['name']
            item[ITEM_ID] = itemxml.attrib['id']
            item[ITEM_CONTENT] = content
            item[ITEM_TYPE] = itemxml.tag
            store_item(ix, app_meta_info, tookit_meta_info, item)


def store_item(ix, app_meta_info, tookit_meta_info, item):
    path = "%s/%s/%s" % (app_meta_info[PROJECT_NAME], app_meta_info[BRANCH_NAME], app_meta_info[SNAPSHOT_NAME])
    # print("storing : "+path+item[ITEM_NAME])
    if tookit_meta_info is not None:
        ix.add_document(
            project_name=app_meta_info[PROJECT_NAME],
            project_id=app_meta_info[PROJECT_ID],
            snapshot_name=app_meta_info[SNAPSHOT_NAME],
            snapshot_id=app_meta_info[SNAPSHOT_ID],
            branch_name=app_meta_info[BRANCH_NAME],
            branch_id=app_meta_info[BRANCH_ID],
            item_name=item[ITEM_NAME],
            item_id=item[ITEM_ID],
            item_type=item[ITEM_TYPE],
            item_content=item[ITEM_CONTENT],
            is_toolkit=True,
            toolkit_project_name=tookit_meta_info[PROJECT_NAME],
            toolkit_project_id=tookit_meta_info[PROJECT_ID],
            toolkit_snapshot_name=tookit_meta_info[SNAPSHOT_NAME],
            toolkit_snapshot_id=tookit_meta_info[SNAPSHOT_ID],
            toolkit_branch_name=tookit_meta_info[BRANCH_NAME],
            toolkit_branch_id=tookit_meta_info[BRANCH_ID],
            apppath=path
        )
    else:
        ix.add_document(
            project_name=app_meta_info[PROJECT_NAME],
            project_id=app_meta_info[PROJECT_ID],
            snapshot_name=app_meta_info[SNAPSHOT_NAME],
            snapshot_id=app_meta_info[SNAPSHOT_ID],
            branch_name=app_meta_info[BRANCH_NAME],
            branch_id=app_meta_info[BRANCH_ID],
            item_name=item[ITEM_NAME],
            item_id=item[ITEM_ID],
            item_type=item[ITEM_TYPE],
            item_content=item[ITEM_CONTENT],
            is_toolkit=False,
            apppath=path
        )


def process_toolkitzip(ix, zf, app_meta_info):
    packagexml = zf.open("META-INF/package.xml").read()
    packagexml = ET.fromstring(packagexml)
    tookit_meta_info = get_meta_info(packagexml)
    store_all_items(ix, zf, app_meta_info, tookit_meta_info, packagexml.findall('./objects/object'))


def process_appzip(ix, path):
    zf = zipfile.ZipFile(path)
    packagexml = zf.open("META-INF/package.xml").read()
    packagexml = ET.fromstring(packagexml)
    app_meta_info = get_meta_info(packagexml)
    store_all_items(ix, zf, app_meta_info, None, packagexml.findall('./objects/object'))

    for filename in zf.namelist():
        if filename.endswith('.zip'):
            filedata = io.BytesIO(zf.open(filename).read())
            process_toolkitzip(ix, zipfile.ZipFile(filedata), app_meta_info)


def get_index():
    if not storage.index_exists():
        ix = storage.create_index(Mydocument())
    else:
        ix = storage.open_index()
    return ix


def index_app(path):
    print("started indexing file " + path)
    ix = get_index()
    writer = AsyncWriter(ix)
    process_appzip(writer, path)
    writer.commit()
    ix.close()
    print("indexing completed " + path)


def list_apps():
    result = []
    oix = get_index()
    lst = oix.reader().lexicon("apppath")
    print(oix.doc_count())
    for l in lst:
        print(l)
        result.append(l.decode("utf-8"))
    return result


def search_text(query):
    output = []
    oix = storage.open_index()
    qp = QueryParser(ITEM_CONTENT, schema=Mydocument())
    q1 = qp.parse(query)
    with oix.searcher() as s:
        results = s.search(q1, limit=500)
        print(results.is_empty())
        results.fragmenter.maxchars = 300
        results.fragmenter.surround = 300
        for result in results:
            output.append(({'app': result['apppath'], 'item_name': result[ITEM_NAME],
                            'snippet': result.highlights("item_content")}))
    return output


def deleteApp(path):
    print("deleting path " + path)
    ix = get_index()
    writer = ix.writer()
    qp = QueryParser(ITEM_CONTENT, schema=Mydocument())
    q1 = qp.parse('apppath:' + path)
    writer.delete_by_query(q1)
    writer.commit()
    ix.close()


q = Queue()
task_count = Queue()


def index_worker():
    while True:
        item = q.get()
        index_app(item)
        q.task_done()
        task_count.get()
        task_count.task_done()


@app.route('/')
def r1():
    return render_template('index.html')


@app.route('/importApp', methods=["GET"])
def r2():
    path = request.args.get('twxpath')
    q.put(path)
    task_count.put(path)
    return "OK"


@app.route('/inprogress', methods=["GET"])
def r3():
    return str(task_count.qsize())


@app.route('/listApps', methods=["GET"])
def r4():
    return json.dumps(list_apps())


@app.route('/search', methods=["GET"])
def r5():
    q = request.args.get('q')
    print(q)
    return json.dumps(search_text(q))


@app.route('/deleteApp', methods=["GET"])
def r6():
    path = request.args.get('twxpath')
    deleteApp(path)
    return "OK"


t = Thread(target=index_worker)
t.daemon = True
t.start()

app.run(port=config.PORT, debug=True)
