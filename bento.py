import sublime, sublime_plugin
import os
from os import walk
from os import listdir
from os.path import isfile, join

settings = {}

def init_plugin():
    global settings

    # Setup settings
    settings = sublime.load_settings('bentoamd.sublime-settings')

    # I guess these reload on settings change?
    settings.clear_on_change('reload')
    settings.add_on_change('reload', init_plugin)

def plugin_loaded():
    init_plugin()

class BentoAmdCommand(sublime_plugin.TextCommand):

    def on_done(self, index):
        if index == -1:
            return
        print(self.files[index])
        file = open(self.files[index], 'rb').read().decode('utf-8')
        a = file.find('bento.define(\'')+14
        b = file.find('\'',a)

        modulePath = file[a:b]

        #TODO: find actual alias defined in file...
        moduleName = self.names[index].split('/').pop()
        moduleName = moduleName.capitalize()

        a = file.find('@moduleName')
        if (a != -1):
            a += 12
            b = file.find('\n', a)
            moduleName = file[a:b]


        print(modulePath, moduleName)
        # TODO: edit current file and insert name + alias
        view = sublime.active_window().active_view()
        regions = view.find_by_selector('meta.function.anonymous.js') + view.find_by_selector('punctuation.definition.brackets.js')

        modulePath = "\t\'"+modulePath+"\'"
        moduleName = "\t"+moduleName

        pathPos = -1
        namePos = -1

        arrayStart = -1;

        for region in regions:
            char = view.substr(region)[-1]
            if (char == '['):
                arrayStart = region.a
            if (char == ']' and pathPos == -1):
                l = region.b - arrayStart
                #TODO this isn't exactly foolproof
                if (l > 10):
                    modulePath = ",\n"+modulePath
                pathPos = region.b - 2

            if (char == ')' and namePos == -1):
                #TODO this isn't exactly foolproof
                if (region.b - region.a > 17):
                    moduleName = ",\n"+moduleName
                namePos = region.b - 2

        #the inserts get combined into one command, so a single cmd+z undoes them
        view.run_command("bento_insert", {"args":{"content": [modulePath, moduleName], "pos" : [pathPos, namePos]}})

        return

    def run(self, edit):
        window = sublime.active_window()
        view = self.view
        # get folders in folder pane
        folders = window.folders();
        # prepare to collect names and paths
        self.names = []
        self.files = []
        # quick panel needs a list of string lists
        self.qpanel = []
        #find root folder of current file
        current = window.active_view().file_name()
        # enumerate js folders
        for folder in folders:
            path = os.path.join(folder, "js")
            if os.path.isdir(path):
                #unsure wether this will work on windows too
                root = folder.split('/').pop()
                if (current.count(folder) == 0 and root != 'Bento'):
                    continue

                for (dirpath, dirnames, filenames) in walk(path):
                    f = []
                    n = []
                    for filename in filenames:
                        # string list
                        q = []
                        filepath = os.path.join(dirpath, filename) #get full path
                        name = filepath[(len(path) + 1):]
                        name = name[:-3] #cut off .js

                        if (root == 'Bento'):
                            name = 'bento/'+name;

                        f.append(filepath)
                        n.append(name)
                        # create stringlist of name+path
                        q.append(name)
                        q.append(filepath)
                        # add to quick panel
                        self.qpanel.append(q)

                    # append the paths and names
                    self.files.extend(f)
                    self.names.extend(n)

        # show quick panel
        window.show_quick_panel(self.qpanel, self.on_done)


class BentoInsertCommand(sublime_plugin.TextCommand):
    def run(self, edit, args):
        ii = len(args['pos'])
        while ii > 0:
            ii -= 1
            self.view.insert(edit, args['pos'][ii], args['content'][ii])
