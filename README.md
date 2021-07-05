# Dialogue Flow Framework

The Dialogue Flow Framework (DFF) is a dialogue systems development environment that supports both rapid prototyping and long-term team development workflows for dialogue systems. This framework is based on Emora STDM (E-STDM). A simple structure allows easily building and visualizing a dialogue graph.

Links: [Github](https://github.com/deepmipt/dialog_flow_framework)

# Quick Start

## Installation
```
pip install dff
```


# Description

DFF was designed during the process of E-STDM adaptation to DREAM 2 Socialbot architecture. E-STDM has a large set of modules that can be used out of the box, but these modules are not optional and are always loaded with the program which increases the resources consumption of the service. Using pre-built modules can be inconvenient when we need to include all of the related modules. For these cases, E-STDM suggests writing your own modules, but writing one such module may seem redundant, and if there are many such modules, then it becomes not easy to work with them. As we already have our own large library of text-processing functions, we had to strip down similar functionality from the original solution. E-STDM's integration into our system turned to be a complicated process.

All these disadvantages led to the fact that we built our own framework DFF} on the top of E-STDM. Working with the framework is organized in such a way that writing a dialogue script in python} is as simple, fast, and flexible as possible, and the framework also consumes an order of magnitude less memory than E-STDM. A special extension was made for the framework, which accelerated the writing of the script in cases where the standard set of functions is sufficient. 

Recently, a variety of frameworks for the development of dialogue flows have appeared to speed up the process of creating a dialogue system. They often allow developers to customize natural language understanding (NLU) modules and control dialogues using state machines. Other frameworks require more expertise but give a more fine-grained control by following the formulation of the dialogue control information state. This information state-based design provides support for complex interactions but sacrifices the intuitiveness and speed of developing state machine-based dialogue flows. 

There are many frameworks that rely on designing the flow of conversation. This requires experience with specific frameworks, and rapid prototyping in these environments puts a lot of constraints on the developer. Still, in these approaches dialogue management focuses primarily on shallow pattern-response pairs making it difficult to model complex interactions. 
