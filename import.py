import pickle
from ScriptingBridge import *
from Foundation import *
import os
import sys
from rtm import RTM
import webbrowser


CONFIG_DIR = ".things2rtm"
CONFIG_PATH = os.path.expanduser("~/" + CONFIG_DIR)
if not os.path.exists(CONFIG_PATH):
    os.mkdir(CONFIG_PATH)

EXPORT_PATH = os.path.join(CONFIG_PATH, "export.log")
IMPORT_LOG_PATH = os.path.join(CONFIG_PATH, "import.log")
TOKEN_PATH = os.path.join(CONFIG_PATH, "token")

class ThingsHelper(object):
    def __init__(self):
        self.things = SBApplication.applicationWithBundleIdentifier_('com.culturedcode.things')

    def get_areas(self):
        for area in self.things.areas():
            yield area.name()

    def get_tasks(self, area_name = None):
        if area_name:
            list = [list for list in self.things.lists() if list.name() == area_name][0]
        else:
            list = self.things
        for things_task in list.toDos():
            #canceled = 1952736108
            #completed = 1952736109
            #open = 1952737647
            if things_task.status() == 1952737647:
                task = {
                    'id': things_task.id(),
                    'name': things_task.name(),
                    'tags': [tag.name() for tag in things_task.tags()],
                    'is_complete': (things_task.status() != 1952737647),
                    'due_date': str(things_task.dueDate()).split(' ')[0] if things_task.dueDate() else None,
                    'area': things_task.area().name() if things_task.area() else None,
                    'project': things_task.project().name() if things_task.project() else None,
                    'notes': things_task.notes()
                }
                yield task

class ImportLog(object):
    def __init__(self):
        self.log = self._read()

    def write_entry(self, entry):
        f = open(IMPORT_LOG_PATH, 'a')
        f.write(entry + "\n")
        f.close()
        self.log.append(entry)

    def exists(self, entry):
        return (entry in self.log)

    def _read(self):
        if os.path.exists(IMPORT_LOG_PATH):
            f = open(IMPORT_LOG_PATH, 'r')
            log = f.read().split('\n')
            log = [entry.replace("\n", "") for entry in log]
            f.close()
            return log
        return []

class RTMHelper(object):
    def __init__(self):
        self._timeline = None
        token = self._get_token()
        self.rtm = RTM('44c0313c5aa5c16cf47ee93b1c4595c7', '7a69d867fcdc2f0d', token)
        if not token:
            webbrowser.open(self.rtm.getAuthURL())
            raw_input("Press enter once you've given access")
            token = self.rtm.getToken()
            self._save_token(token)

    def _get_token(self):
        token = None
        if os.path.exists(TOKEN_PATH):
            f = open(TOKEN_PATH, 'r')
            token = f.read()
            f.close()
        return token

    def _save_token(self, token):
        f = open(TOKEN_PATH, 'w')
        f.write(token)
        f.close()

    def get_timeline(self):
        if not self._timeline:
            self._timeline = self.rtm.timelines.create().timeline
        return self._timeline

    def add_list(self, list_name):
        list = self.rtm.lists.add(timeline = self.get_timeline(), name = list_name.replace(" ", "_"))

    def add_task(self, task):
        new_task = task['name']
        if task['area']:
            new_task += " #"+task['area'].replace(" ", "_")
        if task['project']:
            new_task += " #"+task['project'].replace(" ", "_")

        tags = " #".join([tag.replace(" ", "_") for tag in task['tags']]) if len(task['tags']) != 0 else None
        if tags:
            new_task += " #"+tags
        if task['due_date']:
            new_task += " ^"+task['due_date']
        
        #print new_task
        #return
        rtm_task = self.rtm.tasks.add(timeline = self.get_timeline(), name = new_task, parse = 1)
        if task['is_complete']:
            self.rtm.tasks.complete(timeline = self.get_timeline(), list_id = rtm_task.list.id, taskseries_id = rtm_task.list.taskseries.id, task_id = rtm_task.list.taskseries.task.id)
        if task['notes']:
            self.rtm.tasksNotes.add(timeline = self.get_timeline(), list_id = rtm_task.list.id, taskseries_id = rtm_task.list.taskseries.id, task_id = rtm_task.list.taskseries.task.id, note_title = "Note", note_text = task["notes"])
        #name
        #due date ^
        #priority !
        #list and tags #
        #location @
        #repeat *
        #estimate =

def export_from_things():
    things = ThingsHelper()
    data = {
        'areas': [],
        'tasks': []
    }
    areas = things.get_areas()
    for i, area in enumerate(areas):
        print "%d) Exporting: %s" % (i, area)
        data['areas'].append(area)


    tasks = things.get_tasks()
    for i, task in enumerate(tasks):
        try:
            print "%d) Exporting: %s" % (i, task['name'].encode('ascii', 'ignore'))
        except:
            print "%d) Exporting: %s" % (i, task)
        data['tasks'].append(task)

    f = open(EXPORT_PATH, 'wb')
    pickle.dump(data, f)
    f.close()

def import_to_rtm():
    f = open(EXPORT_PATH, 'rb')
    data = pickle.load(f)
    f.close()
    rtm = RTMHelper()
    log = ImportLog()

    def import_areas():
        #areas
        for area in data['areas']:
            if not log.exists(area):
                print "Adding List: %s" % (area)
                rtm.add_list(area)
                log.write_entry(area)
            else:
                print "Skipping List: %s" % (area)
    
    def import_tasks():
        #tasks
        for i, task in enumerate(data['tasks']):
            if not log.exists(task['id']) and not task['is_complete']:
                try:
                    print "%d) Importing: %s" % (i, task['name'])
                    rtm.add_task(task)
                    log.write_entry(task['id'])
                except KeyboardInterrupt:
                    break
                except:
                    print "%d) Error Importing %s (%s)" % (i, task, sys.exc_info()[0])
            else:
                print "%d) Skipping: %s" % (i, task['name'])

    import_areas()
    import_tasks()

def main(args):
    if len(args) == 0 or args[0] == "export":
        export_from_things()
    if len(args) == 0 or args[0] == "import":
        import_to_rtm()

if __name__ == "__main__": main(sys.argv[1:])
