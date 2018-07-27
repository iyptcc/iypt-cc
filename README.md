# IYPTcc GLUE

GLUE is the main orchestrating component for the IYPT control center.

## CI

the project is built and tested in the Gitlab CI with status

[![build status](https://git.nlogn.org/CC/GLUE/badges/master/build.svg)](https://git.nlogn.org/CC/GLUE/commits/master)

and

[![coverage report](https://git.nlogn.org/CC/GLUE/badges/master/coverage.svg)](https://git.nlogn.org/CC/GLUE/commits/master)


## Development

To ensure a consistent development, the following naming rules are set:

### URLs

Url names are in the form of app_name:local_name

The local name should be in the form:

action\[_filter\]_object\[s\]

#### action
The action should be one of:

* add
* change
* delete

but is not limited by these.

If the action would be *view* it is omitted.

If the action would be *list* it is also omitted.

The differentiation is in the plural of the object.

#### filter

A filter specifies a subset of objects on which the action is applied.

#### object

Prefereably this is a ContentType, removing all _ and all lower case.

It will have a plural *s* if the action is applied to all objects, like with *list*.

#### Examples

|name| explanation |
| --- | --- |
| applications | list all applications |
| application | show a specific application |
| team_application | show specific application regarding a team |
| add_application | action to create a generic application
| add_role_application | action to create a application for a role |
| change_application | change an existing application |
| change_applicatoins | change all applications |
| accept_teammember_application | accept a specific application of a team member |
| change_participationdatas | change all participation data (display it also) |
| team | show team with overview |



### Templates

The templates should be named after the url, if possible.

The django convention to append *_form* for form only views is kept.

For Preview pages (stage 2 of formtool) *_preview* is appended.

