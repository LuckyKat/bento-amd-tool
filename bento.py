import sublime, sublime_plugin
import re
import os
from os import walk
from os import listdir
from os.path import isfile, join

settings = {}
completions = {}

def init_plugin():
    global settings

    # Setup settings
    settings = sublime.load_settings('bentoamd.sublime-settings')

    # I guess these reload on settings change?
    settings.clear_on_change('reload')
    settings.add_on_change('reload', init_plugin)

def plugin_loaded():
    init_plugin()

# try to get full path of existing js file of a module path
def getFullPath(path):
    currentFolder = ''
    bentoFolder = ''
    currentFile = sublime.active_window().active_view().file_name()

    #find root folders
    for folder in sublime.active_window().folders():
        p = os.path.join(folder, "js")
        if (folder.split(os.sep)[-1].lower() == "bento"):
            bentoFolder = os.path.join(folder, "js")
        if os.path.isdir(p):
            if(currentFile.count(p) != 0):
                currentFolder = p
                if(bentoFolder == ''):
                    bentoFolder = folder.split(os.sep)
                    bentoFolder.pop()
                    bentoFolder = os.sep.join(bentoFolder)
                    bentoFolder = os.path.join(bentoFolder, "Bento" + os.sep +"js")


    fullPath = ''
    if (path.split('/')[0] == 'bento'):
        fullPath = bentoFolder
        path = re.sub('bento/','',path)
    else:
        fullPath = currentFolder

    if (path == 'bento'):
        fullPath += '/bento.js'
    else:
        fullPath += '/'+path+'.js'
    
    if (os.path.isfile(fullPath) == False):
        # file doesn't exist, try js/modules
        fullPath = fullPath.replace('js/' ,'js/modules/')
        if (os.path.isfile(fullPath)):
            return fullPath
        else:
            return ''
    else:
        return fullPath

# event listener when st presents completions
class CompletionListener(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        out = []
        for key in completions:
            snippets = completions[key]
            for snippet in snippets:
                # TODO: only show snippet if it's available in module list 
                out.append(snippet)
        return out

# ready paths and find snippets from files
def findSnippets(view):
    # read dependencies and add completions
    global completions
    brackets = view.find_by_selector('punctuation.definition.brackets.js') + view.find_by_selector('meta.brackets.js')
    paths = sublime.Region(brackets[0].a, brackets[0].b)
    paths = view.substr(paths)
    paths = paths.split('\n')
    paths.pop();
    del paths[0]
    paths = "".join(paths)
    paths = re.sub('[\'\t\s]','',paths).split(',')

    sheets = sublime.active_window().sheets()
    fileNames = []
    for sheet in sheets:
        fileNames.append(os.path.abspath(sheet.view().file_name()))

    for path in paths:
        # read the file and find 
        fullPath = getFullPath(path)
        fullPath = os.path.abspath(fullPath)

        # already cached?
        # unless the tab is open
        if (fullPath in completions and fullPath not in fileNames):
            continue
        if (fullPath):
            # open file and inspect
            # even if the file has no snippet, we cache the result so it doesnt have to be opened again
            snippets = inspectFile(fullPath)
            # cache result
            completions[fullPath] = snippets

# open file and search for snippet
def inspectFile(path):
    # read file
    file = open(path, 'r').read()
    # find the line with @snippet
    isSearching = True
    searchPos = 0
    snippets = []
    while True:
        snippetPos = file.find('@snippet', searchPos)
        if (snippetPos < 0):
            # no snippets found
            break

        # skip the word snippet itself
        snippetPos += 9
        snippetNamePos = file.find('\n', snippetPos)
        endPos = file.find(' *', snippetNamePos)

        snippetName = file[snippetPos: snippetNamePos];
        snippet = file[snippetNamePos: endPos];

        # strip whitespaces
        snippetName = snippetName.strip()
        snippet = snippet.strip()
        snippets.append([snippetName, snippet])
        
        # prepare for searching next snippet
        searchPos = endPos

    return snippets

# event listener when st opens a file
class OpenListener(sublime_plugin.EventListener):
    def on_load_async(self, view):
        findSnippets(view)
        return 
    # update snippet on saving
    def on_post_save_async(self, view):
        snippets = inspectFile(view.file_name())
        print(snippets)
        # update snippet 
        completions[fullPath] = snippets
        return
    
class BentoAmdCommand(sublime_plugin.TextCommand):

    def on_done(self, index):
        if index == -1:
            return
        print(self.files[index])
        file = open(self.files[index], 'r').read()
        a = file.find('bento.define(\'')+14
        b = file.find('\'',a)

        modulePath = file[a:b]

        moduleName = self.names[index].split('/').pop()
        moduleName = moduleName.capitalize()

        #Try to find actual alias defined in file
        a = file.find('@moduleName ')
        if (a != -1):
            a += 12
            b = file.find('\n', a)
            moduleName = file[a:b]

        view = sublime.active_window().active_view()
        regions = view.find_by_selector('meta.function.anonymous.js') + view.find_by_selector('punctuation.definition.brackets.js') + view.find_by_selector('meta.brackets.js')

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

        # refresh snippets
        findSnippets(view)

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
                        if(name[-3:] != '.js'):
                            continue

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




class BentoDefinitionCommand(sublime_plugin.TextCommand):
    def run(self, edit, event):
        #TODO open file at path in new windo
        word = self.view.substr(self.view.word(self.view.window_to_text([event['x'],event['y']])))

        #get index in modules list
        modules = self.view.substr(self.view.find_by_selector('meta.function.anonymous.js')[0])
        modules = modules.split('\n')
        modules.pop()
        del modules[0]
        modules = "".join(modules)
        modules = re.sub('[\t\s]', '', modules).split(',')

        if (modules.count(word) == 0):
            print('not a module')
            return

        moduleIndex = modules.index(word)

        #find matching path
        brackets = self.view.find_by_selector('punctuation.definition.brackets.js') + self.view.find_by_selector('meta.brackets.js')
        paths = sublime.Region(brackets[0].a, brackets[0].b)
        paths = self.view.substr(paths)
        paths = paths.split('\n')
        paths.pop();
        del paths[0]
        paths = "".join(paths)
        paths = re.sub('[\'\t\s]','',paths).split(',')

        path = paths[moduleIndex]

        currentFolder = ''
        bentoFolder = ''
        currentFile = sublime.active_window().active_view().file_name()

        #find root folders
        for folder in sublime.active_window().folders():
            p = os.path.join(folder, "js")
            if (folder.split(os.sep)[-1].lower() == "bento"):
                bentoFolder = os.path.join(folder, "js")
            if os.path.isdir(p):
                if(currentFile.count(p) != 0):
                    currentFolder = p
                    if(bentoFolder == ''):
                        bentoFolder = folder.split(os.sep)
                        bentoFolder.pop()
                        bentoFolder = os.sep.join(bentoFolder)
                        bentoFolder = os.path.join(bentoFolder, "Bento" + os.sep +"js")


        fullPath = ''
        if (path.split('/')[0] == 'bento'):
            fullPath = bentoFolder
            path = re.sub('bento/','',path)
        else:
            fullPath = currentFolder

        if (path == 'bento'):
            fullPath += '/bento.js'
        else:
            fullPath += '/'+path+'.js'
        
        if (os.path.isfile(fullPath) == False):
            # file doesn't exist, try js/modules
            fullPath = fullPath.replace('js/' ,'js/modules/')
            sublime.active_window().open_file(fullPath)
        else:
            sublime.active_window().open_file(fullPath)

        return

    def want_event(self):
        return True

