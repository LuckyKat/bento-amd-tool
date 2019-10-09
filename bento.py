import sublime, sublime_plugin
import re
import os
from os import walk
from os import listdir
from os.path import isfile, join
import io

settings = {}
completions = {}

def init_plugin():
    global settings

    # Setup settings
    settings = sublime.load_settings('bentoamd.sublime-settings')

    # I guess these reload on settings change?
    settings.clear_on_change('reload')
    settings.add_on_change('reload', init_plugin)

    # user must add this setting!
    # "auto_complete_triggers": [{"selector": "source.js", "characters": "."}]


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
        if folder.split(os.sep)[-1].lower() == "bento":
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
    if path.split('/')[0] == 'bento':
        fullPath = bentoFolder
        path = re.sub('bento/','',path)
    else:
        fullPath = currentFolder

    if path == 'bento':
        fullPath += '/bento.js'
    else:
        fullPath += '/'+path+'.js'
    
    if not os.path.isfile(fullPath):
        # file doesn't exist, try js/modules
        fullPath = fullPath.replace('js/' ,'js/modules/')
        if os.path.isfile(fullPath):
            return fullPath
        else:
            return ''
    else:
        return fullPath

# event listener when st presents completions
class CompletionListener(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        syntax = view.settings().get('syntax')
        if "JavaScript" not in syntax:
            return None
        out = []

        # get last letter
        region = view.sel()[0]
        region.a = region.a - 1
        lastLetter = view.substr(region)
        lastWord = ''
        definedWord = ''

        lastLine = view.substr(view.line(region))
        column = view.rowcol(region.a)[1]
        # print(view.substr(view.word(region.a + 1)))
        lastWord = lastLine[0:column + 1]
        lastWord = lastWord.strip()
        # the thing you're typing may be inbetween other text, for example "if (...) {"
        lastWordList = re.split('\[|\(|\{| |\:|\;|\,|\+|\-|\*|\/', lastWord)
        lastWord = lastWordList[-1]
        lastLetter = lastWord[-1]

        def addSnippet(snippet):
            # add snippet to the completions list
            dotsInLastWord = lastWord.count('.') + lastLetter.count('.')
            dotsInSnippet = snippet[1].count('.')

            if dotsInSnippet <= 1 or dotsInLastWord == 0 or dotsInSnippet == dotsInLastWord:
                # in these cases, ST will correctly replace the whole word
                out.append(snippet)
            else:
                # otherwise ST will only replace whatever comes after the last dot
                # so we have to trim the front of the snippet accordingly
                lastDotPos = len(lastWord)
                if lastLetter != '.':
                    lastDotPos = lastWord.rfind('.')
                out.append([snippet[0], snippet[1][lastDotPos+1:]])

        if lastLetter == '.':
            # remove dot
            lastWord = lastWord[:-1]

            # try to find the definition of this
            body = view.substr(sublime.Region(0, view.size()))
            definition = lastWord + ' = new '
            defIndex = body.find(definition)
            if defIndex >= 0:
                # get the constructor word
                defLine = view.substr(view.line(defIndex))
                defWord = defLine.split(' = new ')[1].split('(')[0]
                definedWord = defWord
        else:
            # find the string after the last whitespace
            lastWord = lastWord.rsplit(' ', 1)[-1]

        if lastLetter != '.':
            for key in completions:
                if not shouldShowSnippet(key):
                    continue
                snippets = completions[key]
                for snippet in snippets:
                    # ignore the snippets that start with #
                    leftWord = snippet[0]
                    if leftWord.startswith('#'):
                        continue
                    # the word typed so far must be an exact match so far
                    if lastWord.startswith(leftWord[0:len(lastWord)]):
                        addSnippet(snippet)
        else:
            # dot completion
            for key in completions:
                snippets = completions[key]
                for snippet in snippets:
                    if not shouldShowSnippet(key):
                        continue
                    leftWord = snippet[0].split('\t')[0]
                    # return the snippets that match exactly left of the .
                    if leftWord.startswith(lastWord):
                        addSnippet(snippet)
                    # match objects
                    if definedWord != '' and leftWord.startswith('#' + definedWord):
                        sn0 = snippet[0].replace('#' + definedWord + '.', '')
                        out.append([sn0, snippet[1]])
        return out

def shouldShowSnippet(path):
    # only show snippets if it originates from the same project or Bento
    currentFile = sublime.active_window().active_view().file_name()

    # is it from bento?
    isBento = path.lower().find('/bento/js')
    if isBento >= 0:
        return True

    # extract path up to /js
    originIndex = currentFile.find(os.path.sep + 'js')
    if originIndex < 0:
        # not a bento project?
        return False

    origin = currentFile[:originIndex]

    # check if path up to /js is similar
    return path.startswith(origin)

# get the paths of all required modules in the given view
def getRequirePaths(view):
    brackets = view.find_by_selector('meta.sequence.js') + view.find_by_selector('meta.brackets.js')
    if len(brackets) == 0:
        return []
    paths = sublime.Region(brackets[0].a, brackets[0].b)
    paths = view.substr(paths)
    paths = paths.split('\n')
    paths.pop()
    if len(paths) > 0:
        del paths[0]
    paths = "".join(paths)
    paths = re.sub('[\'\t\s]','',paths).split(',')
    return paths

# ready paths and find snippets from files
def findSnippets(view):
    # read dependencies and add completions
    global completions

    paths = getRequirePaths(view)

    sheets = sublime.active_window().sheets()
    fileNames = []
    for sheet in sheets:
        fileName = sheet.view().file_name()
        if not fileName:
            continue
        fileNames.append(os.path.abspath(fileName))

    for path in paths:
        # read the file and find 
        fullPath = getFullPath(path)
        fullPath = os.path.abspath(fullPath)

        # already cached?
        # unless the tab is open
        if fullPath in completions and fullPath not in fileNames:
            continue
        if fullPath:
            # open file and inspect
            # even if the file has no snippet, we cache the result so it doesnt have to be opened again
            snippets = inspectFile(fullPath)
            # cache result
            completions[fullPath] = snippets

endOfSnippetName = re.compile(r"([\r\n])|(\*/)")
endOfSnippet = re.compile(r"([\r\n]\s*\*)|(\*/)")

def getMatchPos(regex, str, startPos):
    match = regex.search(str, startPos)
    if match is None: return -1
    else: return match.start()

# open file and search for snippet
def inspectFile(path):
    if not path.endswith(".js"):
        return []
    # read file
    with io.open(path, "r", encoding="utf-8") as my_file:
        try:
            file = my_file.read() 
        except:
            return []

    # find the line with @snippet
    isSearching = True
    searchPos = 0
    snippets = []
    while True:
        snippetPos = file.find('@snippet', searchPos)
        if snippetPos < 0:
            # no snippets found
            break

        # skip the word snippet itself
        snippetPos += 9
        snippetNamePos = getMatchPos(endOfSnippetName, file, snippetPos)
        endPos = getMatchPos(endOfSnippet, file, snippetNamePos)

        snippetName = file[snippetPos: snippetNamePos]
        snippet = file[snippetNamePos: endPos]

        # replace dots with tabs
        # Bug in sublime???
        snippetName = snippetName.replace("|", "\t")

        # un-indent the whole snippet
        leadingWhitespace = snippet[:len(snippet)-len(snippet.lstrip())].strip("\r\n")
        lines = snippet.splitlines(True)
        for i, s in enumerate(lines):
            if s.startswith(leadingWhitespace):
                lines[i] = s[len(leadingWhitespace):]
        snippet = "".join(lines)

        # strip whitespaces
        snippetName = snippetName.strip()
        snippet = snippet.strip()

        # if snippet is empty, we can use the snippet name as its body
        if snippet == "":
            snippet = snippetName.split("\t")[0]
        
        snippets.append([snippetName, snippet])
        
        # prepare for searching next snippet
        searchPos = endPos

    return snippets

# event listener when st opens a file
class OpenListener(sublime_plugin.EventListener):
    def on_load_async(self, view):
        syntax = view.settings().get('syntax')
        if "JavaScript" not in syntax:
            return None
        findSnippets(view)
        return 
    def on_activated_async(self, view):
        syntax = view.settings().get('syntax')
        if "JavaScript" not in syntax:
            return None
        findSnippets(view)
        return 
    # update own snippet on saving
    def on_post_save_async(self, view):
        syntax = view.settings().get('syntax')
        if "JavaScript" not in syntax:
            return None
        fullPath = os.path.abspath(view.file_name())
        snippets = inspectFile(fullPath)
        # print(snippets)
        # update snippet 
        completions[fullPath] = snippets
        return

class BentoAmdCommand(sublime_plugin.TextCommand):

    def on_done(self, index):
        view = sublime.active_window().active_view()
        syntax = view.settings().get('syntax')
        if "JavaScript" not in syntax:
            return None

        if index == -1:
            return

        print("Adding module:", self.files[index])

        with io.open(self.files[index], "r", encoding="utf-8") as my_file:
            file = my_file.read() 

        a = file.find('bento.define(\'')+14
        b = file.find('\'',a)

        modulePath = file[a:b]

        if modulePath in getRequirePaths(view):
            print("Module is already added!")
            return

        moduleName = self.names[index].split('/').pop()
        moduleName = moduleName.capitalize()

        #Try to find actual alias defined in file
        a = file.find('@moduleName ')
        if a != -1:
            a += 12
            b = file.find('\n', a)
            moduleName = file[a:b]

        regions = view.find_by_selector('meta.function.declaration.js') \
                + view.find_by_selector('punctuation.definition.brackets.js') \
                + view.find_by_selector('meta.sequence.js') \
                + view.find_by_selector('meta.brackets.js')

        modulePath = "\t\'"+modulePath+"\'"
        moduleName = "\t"+moduleName

        pathPos = -1
        namePos = -1

        arrayStart = -1

        for region in regions:
            char = view.substr(region)[-1]
            if char == '[':
                arrayStart = region.a
            if char == ']' and pathPos == -1:
                l = region.b - arrayStart
                #TODO this isn't exactly foolproof
                if l > 10:
                    modulePath = ",\n"+modulePath
                pathPos = region.b - 2

            if char == ')' and namePos == -1:
                #TODO this isn't exactly foolproof
                if region.b - region.a > 17:
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
        folders = window.folders()
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
                root = folder.split(os.path.sep).pop()
                if current is not None and current.count(folder) == 0 and root != 'Bento':
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

                        if root == 'Bento':
                            name = 'bento/'+name


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
        modules = self.view.substr(self.view.find_by_selector('meta.function.declaration.js')[0])
        modules = modules.split('\n')
        modules.pop()
        del modules[0]
        modules = "".join(modules)
        modules = re.sub('[\t\s]', '', modules).split(',')

        if modules.count(word) == 0:
            print('not a module')
            return

        moduleIndex = modules.index(word)

        #find matching path
        brackets = self.view.find_by_selector('meta.sequence.js') + self.view.find_by_selector('meta.brackets.js')
        paths = sublime.Region(brackets[0].a, brackets[0].b)
        paths = self.view.substr(paths)
        paths = paths.split('\n')
        paths.pop()
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
            if folder.split(os.sep)[-1].lower() == "bento":
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
        if path.split('/')[0] == 'bento':
            fullPath = bentoFolder
            path = re.sub('bento/','',path)
        else:
            fullPath = currentFolder

        if path == 'bento':
            fullPath += '/bento.js'
        else:
            fullPath += '/'+path+'.js'
        
        if not os.path.isfile(fullPath):
            # file doesn't exist, try js/modules
            fullPath = fullPath.replace('js/' ,'js/modules/')
            sublime.active_window().open_file(fullPath)
        else:
            sublime.active_window().open_file(fullPath)

        return

    def want_event(self):
        return True

