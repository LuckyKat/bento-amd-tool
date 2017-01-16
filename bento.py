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

        file = self.files[index]
        print(file)
        # TODO: open this file and find the real module name + alias
        # TODO: edit current file and insert name + alias
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

