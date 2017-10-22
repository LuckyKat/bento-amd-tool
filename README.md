# Bento AMD Tool

Sublime Text plugin for helping with dependencies in Bento. Bento works with a RequireJS system and it's quite annoying writing down the depenent modules. This tool helps adding these dependencies with a simple shortcut. It also adds snippets/completions defined in these dependencies.

## How to install

No package control support. Install this plugin manually!
Download this repository and place it in the Sublime Text's Packages folder

## Requirements

The project's root folder must be added to the Sublime workspace. If it's inside a subfolder, this plugin will not work!
Also recommended is to have the Bento source code also inside the workspace. This will allow you to add Bento modules and use Bento completions into your files.

## Usage

### Adding depedencies

Default keyboard shortcut for the tool is cmd+alt+b. Type in the module you want to add.
When creating new modules, add a `@moduleName ModuleName` comment in JSDoc style to indicate the name of this module.

### Snippets

The tool will read snippets/completions from modules. Write `@snippet Trigger.Hint` (the Hint is optional). Write down the snippet below this line. The snippet ends when the following line begins with ` *`.

Be careful of writing the snippet trigger and hint, because using certain characters here will break other completions. This is probably a Sublime bug (see this Sublime Text issue https://github.com/SublimeTextIssues/Core/issues/1061)
The dot `.` here is replaced by a tab.
