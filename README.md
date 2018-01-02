# Bento AMD Tool

Sublime Text plugin for helping with dependencies in Bento. Bento works with a RequireJS system and it's quite annoying writing down the depenent modules. This tool helps adding these dependencies with a simple shortcut. It also adds snippets and rudimentary completions defined in these dependencies.

## How to install

No package control support. Install this plugin manually! Download this repository and place the folder in the Sublime Text's Packages folder. Rename the folder to `BentoAMD`.

You must also add `"auto_complete_triggers": [{"selector": "source.js", "characters": "."}]` to your sublime settings to enable the trigger for completions.

## Requirements

The project's root folder must be added to the Sublime workspace. If it's inside a subfolder, this plugin will not work! The plugin looks for javascipt files in `/<Project Name>/js`.

Also recommended is to have the Bento source code also inside the workspace. This will allow you to add Bento modules and use Bento completions into your files.

## Usage

### Adding depedencies

Default keyboard shortcut for the tool is cmd+alt+b. Type in the module you want to add.
When creating new modules, add a `@moduleName ModuleName` comment in JSDoc style to indicate the name of this module.

### Snippets

The tool will read snippets/completions from modules. Write `@snippet Trigger` or `@snippet Trigger|Hint` (a hint is optional, but I recommend adding it). Write down the snippet below this line. The snippet ends when the following line begins with `*`.

Example:
```
/**
 * This module does awesome stuff
 * @moduleName Awesome
 * @snippet Awesome|constructor
Awesome({
    name: '${1:awesome}',
    onComplete: function () {
        $2
    }
})
 */
```

Be careful of writing the snippet trigger and hint, because using certain characters here will break other completions. This is probably a Sublime bug (see this Sublime Text issue https://github.com/SublimeTextIssues/Core/issues/1061)
The dot `.` and pipe `|` is allowed with the auto_complete_triggers setting, and the tool replaces the pipe.

### Completions

The tool adds rudimentary completions. A completion is only triggered if the code has a definition somewhere. For example:
```
// this must be present in the file
var entity = new Entity(); 

// completion can be used here:
entity.
```

To define your own new completions, write a `@snippet`, but start with a `#` to indicate that this is going to be a member variable.

Example:
```
/**
 * This module does awesome stuff
 * @moduleName Awesome
 * @snippet Awesome|constructor
Awesome({
    name: '${1:awesome}',
    onComplete: function () {
        $2
    }
})
 * @snippet #Awesome.getNumber|Number
getNumber();
 * @snippet #Awesome.stuff|snippet
setNumber(${1:0});
 */
```

Quick note: snippets do not have to live 