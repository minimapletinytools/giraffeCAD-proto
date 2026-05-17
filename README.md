# Kumiki

Kumiki is a Code aided Design (CoAD) library for programmatically designing timber framed structures and woodworking in general.

As Kumiki is a CoAD library, it is well suited for usage with AI agents.

Kumiki is used together with Kigumi--a VSCode extension for viewing your kumiki designs!


INSTRUCTIONS BELOW DO NOT WORK YET DO NOT TRY!!!

## setup

Kumiki is best used with Kigumi. To install Kigumi, install [VSCode](https://code.visualstudio.com/) and install the [Kigumi](https://marketplace.visualstudio.com/items?itemName=minimaple.kigumi) extension.

I think Kigumi also requires [python3](https://www.python.org/downloads/), the rest of the depepndencies get installed automagically for you.

You can of course use Kumiki without Kigumi. You can still use Kigumi to setup your Kumiki projects and its dependencies.

## viewing the built in patterns and examples

Kigumi ships with a patternbook and several examples. Open the Kumiki menu by clicking on the Kumiki extension icon in the left side bar.

You may also open Kigumi by opening the command palette in VScode (cmd/ctrl+shift+p). Start typing "kigumi" and choose the "View: Show Kigumi" command. 
You can open a project directly by choosing TODO

## your first kumiki project

Create a folder for your Kumiki project and open that folder in VSCode. Then click "Initialize Project" from the Kumiki menu. You may also run "kigumi: initialize project" command from the command pallete.

TODO finish

## for advanced students

TODO finish


# Contributing

If making changes to Kumiki itself, a separate workflow is used. 

Once you've made your changes, open up a PR. 

## Developing Kumiki

To setup for local development, just check out this repo and use `uv` to manage all your dependencies. The `Makefile` has convenient shortcuts for all your setup and testing needs.

Kigumi has a separate project scanning flow such that it can be used with the Kumiki repo itself as the workspace. Just use Kigumi like you normally would to test Kumiki.

## Developing Kigumi

TODO



# APPENDIX

## FreeCAD and Fusion360 usage

Rendering in FreeCAD and Fusion360 currently requires checking out the entire repo. We do not plan to work around this and support for these tools will be removed soon. 
