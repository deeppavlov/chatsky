
# Dialog Flow Transitions

**Dialog Flow Transitions** is python module add-on for [Dialog Flow Framework](https://github.com/deepmipt/dialog_flow_framework), a free and open-source software stack for creating chatbots, released under the terms of Apache License 2.0.


[Dialog Flow Transitions](../..) allows you to integrate various pre-trained machine learning models for Natural Language Understanding (NLU) into your conversation logic. These include language modelling tools provided by Sklearn, Gensim, and Hugging Face, as well as cloud-hosted services, like Rasa NLU server or Google Dialogflow.
[![Codestyle](../../../workflows/codestyle/badge.svg)](../../../actions)
[![Tests](../../../workflows/test_coverage/badge.svg)](../../../actions)
[![License Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
![Python 3.6, 3.7, 3.8, 3.9](https://img.shields.io/badge/python-3.6%20%7C%203.7%20%7C%203.8%20%7C%203.9-green.svg)

<!-- TODO: uncomment one of these to add badges to your project description -->
<!-- [![Documentation Status](https://df_extended_conditions.readthedocs.io/en/stable/?badge=stable)]() See readthedocs.io -->
<!-- [![Coverage Status]()]() See coveralls.io -->
<!-- [![PyPI](https://img.shields.io/pypi/v/df_extended_conditions)](https://pypi.org/project/df_extended_conditions/) -->
<!-- [![Downloads](https://pepy.tech/badge/df_extended_conditions)](https://pepy.tech/project/df_extended_conditions) -->

# Quick Start
## Installation

The default installation option is to install the package with no dependencies, since normally
machine learning libraries take up a lot of space. However, you can install the package with one or several extras, all of which are listed below.

```bash
pip install df_extended_conditions
pip install df_extended_conditions[dialogflow] # google dialogflow
pip install df_extended_conditions[hf] # hugging face
pip install df_extended_conditions[gensim] # gensim
pip install df_extended_conditions[sklearn] #sklearn
pip install df_extended_conditions[all] # all of the above
```

## Instantiate a model

The library provides a number of wrappers for different model types. All these classes implement a uniform interface.

 - `namespace_key` should be used in all types of models, so that the annotation results are saved to separate namespaces in the context. 
 - The `model` parameter is set with whatever is required to query the model of choice. For Gensim, Sklearn, or Hugging Face, this is an instance of a model. For Google Dialogflow, this is a parsed json of service account credentials. See the class documentation for an exact definition.

However, some of the parameters are class-specific.

 - The `tokenizer` parameter is only required for Sklearn, Gensim, and Hugging Face models. See the signature of the corresponding classes for more information.
 - `device` parameter is only required for Hugging Face models. Use torch.device("cpu") or torch.device("cuda").
 - `dataset` should be passed to all cosine matchers, so that they have a pre-defined set of labels and examples, against which user utterances will be compared.

Using the library, you can deploy models locally.

```python
hf_model = HFClassifier(
    model=model,
    tokenizer=tokenizer,
    device=torch.device("cpu")
    namespace_key="HF"
)
```

Another option is to employ remotely hosted services.
For example, to use RASA models for labelling, you will need a running instance of RASA NLU server.
If you provide the server url to the model, it will query RASA each turn for intent
annotation.

```python
rasa_model = RasaModel(
    model="http://my-rasa-server",
    namespace_key="rasa",
)
```

## Use the Model class in your Script graph

The model class is designed to be used in the `PRE_TRANSITION_PROCESSING` section of the dialogue script graph.
Put it into the `GLOBAL` node to query the model each turn, or into a more specific node to perform queries solely at the chosen stages of the dialogue.

```python
script = {
    GLOBAL: {
        PRE_TRANSITION_PROCESSING: {
            "get_intents_from_rasa": rasa_model 
        }
    }
}
```

The extracted values can be accessed in all functions where `Context` is used.
We provide several such functions that can be leveraged as transition conditions.

```python
from df_extended_conditions.conditions import has_cls_label

script = {
    "root": {
        "start": {
            TRANSITIONS: {
                ("next_flow", "next_node"): has_cls_label("user_happy", threshold=0.9, namespace="some_model")
            }
        }
    },
    ...
}
```

To get more advanced examples, take a look at [examples](examples) on GitHub.

# Custom classifier / matcher

In order to create your own classifier, create a child class of the `BaseModel` abstract type. 

`BaseModel` only has one abstract method, `predict`, that should necessarily be overridden. The signature of the method is the following: it takes a request string and returns a dictionary of class labels and their respective probabilities. 

You can override the rest of the methods, namely `save`, `load`, `fit` and `transform` at your own convenience, e.g. lack of those will not raise an error. 
* `fit` should take a new dataset and retrain / update the underlying model.
* `transform` should take a request string and produce a vector.
* `save` and `load` are self-explanatory.

```python
class MyCustomClassifier(BaseModel)
    def predict(self, request: str) -> dict:
        probs = get_probs(request)
        return probs
```

As for your own cosine matcher, to build one, you should inherit from the `CosineMatcherMixin` and from the `BaseModel`, with the former taking precedence. This requires the `__init__` method to take `dataset` argument.

In your class, override the `transform` method that is used to obtain a two-dimensional vector (optimally, a Numpy array) from a string. Unlike the classifier case, the `predict` method is already implemented for you, so you don't have to tamper with it.

Those two steps should suffice to get your matcher up and running.

```python
class MyCustomMatcher(CosineMatcherMixin, BaseModel):
    def __init__(self, model, dataset, namespace_key) -> None:
        CosineMatcherMixin.__init__(self, dataset)
        BaseModel.__init__(self, namespace_key)
        self.model = model
    
    def transform(self, request: str) -> np.ndarray:
        vector = self.model(request)
        return vector
```


# Contributing to the Dialog Flow Transitions

Please refer to [CONTRIBUTING.md](CONTRIBUTING.md).