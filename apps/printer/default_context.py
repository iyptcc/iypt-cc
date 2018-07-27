from .models import Template

# each template type has a default context to test the template with

default_template_context={
    Template.PREVIEW : {
        "fight_id":3324,
        "round":2,
        "room":"A",
        "stages":[
            {"order":1,
             "reporter":"Switzerland",
             "opponent":"China",
             "reviewer":"Germany",
             "problems":[1,3],
             "rejected_reporter":[],
             "presented_reporter":[5],
             "opposed_opponent":[7],
             "presented_opponent":[9],
             "lifted_bans":["a"]
             },
            {"order":2,
             "reporter":"China",
             "opponent":"Germany",
             "reviewer":"Iran",
             "problems":[1,3,6,10,12,15],
             "rejected_reporter":[4],
             "presented_reporter":[4],
             "opposed_opponent":[7],
             "presented_opponent":[],
             "lifted_bans":["a","b"]
             },
            {"order":3,
             "reporter":"Germany",
             "opponent":"Iran",
             "reviewer":"Switzerland",
             "problems":[1,3,5,6,7,8,9,10,11,13,14],
             "rejected_reporter":[4,12],
             "presented_reporter":[],
             "opposed_opponent":[4],
             "presented_opponent":[12],
             "lifted_bans":["a"]
             },
            {"order":4,
             "reporter":"Iran",
             "opponent":"Switzerland",
             "reviewer":"China",
             "problems":[1,3,6,7,8,10,11,12,13,14],
             "rejected_reporter":[4],
             "presented_reporter":[5],
             "opposed_opponent":[],
             "presented_opponent":[9],
             "lifted_bans":["a"]
             },
        ],
        "problems":[
            (1,"Invent"),
            (2,"asd"),
            (3,"bsd"),
            (4,"cfads"),
            (5,"deewa"),
            (6,"easd"),
            (7,"ftrasd"),
            (8,"grasdasd"),
            (9,"htasd"),
            (10,"iasdasd"),
            (11,"jadsf"),
            (12,"kasd"),
            (13,"lasaf"),
            (14,"masdas"),
            (15,"nadsf"),
            (16,"ooasdf"),
            (17,"ppasdf"),
        ]
    },
    Template.RESULTS : {
        "fight_id":3324,
        "round":2,
        "room":"A",
        "stages":[{
            "order":1,
            "reporter_team":"USA",
            "reporter_person_firstname":"Christoper",
            "reporter_person_lastname":"Springfield",
            "opponent_team":"China",
            "opponent_person_firstname":"Chris",
            "opponent_person_lastname":"Field",
            "reviewer_team": "Iran",
            "reviewer_person_firstname": "Chi",
            "reviewer_person_lastname": "Lu",
            "presented":(1,"invent yoursealf"),
            "rejected":[(2,"blub"),(3,"cla")],
            },
            {
            "order":2,
            "reporter_team":"USA",
            "reporter_person_firstname":"Christoper",
            "reporter_person_lastname":"Springfield",
            "opponent_team":"China",
            "opponent_person_firstname":"Chris",
            "opponent_person_lastname":"Field",
            "reviewer_team": "Iran",
            "reviewer_person_firstname": "Chi",
            "reviewer_person_lastname": "Lu",
            "presented":(1,"invent yoursealf"),
            "rejected":[],
            },
            {
            "order":3,
            "reporter_team":"USA",
            "reporter_person_firstname":"Christoper",
            "reporter_person_lastname":"Springfield",
            "opponent_team":"China",
            "opponent_person_firstname":"Chris",
            "opponent_person_lastname":"Field",
            "reviewer_team": "Iran",
            "reviewer_person_firstname": "Chi",
            "reviewer_person_lastname": "Lu",
            "presented":(1,"invent yoursealf"),
            "rejected":[(2,"blub"),(3,"cla")],
            },
{
            "order":4,
            "reporter_team":"USA",
            "reporter_person_firstname":"Hallo",
            "reporter_person_lastname":"Bla",
            "opponent_team":"China",
            "opponent_person_firstname":"Chris",
            "opponent_person_lastname":"Field",
            "reviewer_team": "Iran",
            "reviewer_person_firstname": "Chi",
            "reviewer_person_lastname": "Lu",
            "presented":(1,"invent yoursealf"),
            "rejected":[(2,"blub"),(3,"cla")],
            }
        ],
        "jurors":[
            {"firstname":"Ulrike",
             "lastname":"Regner",
             "stages":[
                 {"reporter":6,"opponent":3,"reviewer":8},
                 {"reporter":6,"opponent":3,"reviewer":8},
                 {"reporter":6,"opponent":3,"reviewer":8},
                 {"reporter":4,"opponent":4,"reviewer":4},
             ]
            },
            {"firstname":"Ulrike",
             "lastname":"Regner",
             "stages":[
                 {"reporter":6,"opponent":3,"reviewer":8},
                 {"reporter":6,"opponent":3,"reviewer":8},
                 {"reporter":6,"opponent":3,"reviewer":8},
                 {"reporter":4,"opponent":4,"reviewer":4},
             ]
            },
            {"firstname":"Ulrike",
             "lastname":"Regner",
             "stages":[
                 {"reporter":6,"opponent":3,"reviewer":8},
                 {"reporter":6,"opponent":3,"reviewer":8},
                 {"reporter":6,"opponent":3,"reviewer":8},
                 {"reporter":4,"opponent":4,"reviewer":4},
             ]
            },
            {"firstname":"Ulrike",
             "lastname":"Regner",
             "stages":[
                 {"reporter":6,"opponent":3,"reviewer":8},
                 {"reporter":6,"opponent":3,"reviewer":8},
                 {"reporter":6,"opponent":3,"reviewer":8},
                 {"reporter":4,"opponent":4,"reviewer":4},
             ]
            },
            {"firstname":"Ulrike",
             "lastname":"Regner",
             "stages":[
                 {"reporter":6,"opponent":3,"reviewer":8},
                 {"reporter":6,"opponent":3,"reviewer":8},
                 {"reporter":6,"opponent":3,"reviewer":8},
                 {"reporter":4,"opponent":4,"reviewer":4},
             ]
            }
        ],
        "average":[
            {"reporter":6,"opponent":3,"reviewer":8},
            {"reporter":6,"opponent":3,"reviewer":8},
            {"reporter":6,"opponent":3,"reviewer":8},
            {"reporter":6,"opponent":3,"reviewer":8},
        ],
        "factor":[
            {"reporter":3,"opponent":2,"reviewer":1},
            {"reporter":3,"opponent":2,"reviewer":1},
            {"reporter":2.6,"opponent":2,"reviewer":1},
            {"reporter":2.6,"opponent":2,"reviewer":1},
        ],
        "points":[
            {"reporter":18,"opponent":6,"reviewer":8},
            {"reporter":18.1,"opponent":6.20,"reviewer":8},
            {"reporter":15,"opponent":6.3,"reviewer":8},
            {"reporter":15,"opponent":6.3,"reviewer":8},
        ],
        "ranking":[
            {"team":"USA", "points":43.2},
            {"team":"China", "points":42.2},
            {"team":"Iran", "points":41},
            {"team":"India", "points":41},
        ]
    },
    Template.JURYROUND : {
        'round_id': 43,
        'round': 1,
        'fights': [{
            'room': 'A',
            'jurors': [('Mattias', 'Andersson'), ('Christa', 'Deinlein'), ('Andrei', 'Klishin'), ('Monsit', 'Tanasittikosol')],
            'chair': ('Samuel', 'Byland')},
            {'room': 'B',
             'jurors': [('Yung-Yuan', 'Hsu'), ('Patrick', 'Lenggenhager'), ('Victor', 'Paunescu'), ('Oleg', 'Yordanov')],
             'chair': ('Valentin', 'Lobyshev'),
             'nonvoting':[('Fefe','Leitner'),('Nyan','Cat')]},
            {'room': 'C',
             'jurors': [('Yury', 'Bashkatov'), ('Iat Neng', 'Chan'), ('Tatyana', 'Gonçalves Stankevicius'), ('Leong', 'Tze Kwang')],
             'chair': ('Nirut', 'Pussadee')},
            {'room': 'D',
             'jurors': [('Chuanyong', 'Li'), ('Michael', 'Steck'), ('Simon', 'Whittaker'), ('Young-Gui', 'Yoon')],
             'chair': ('Gavin', 'Jennings')},
            {'room': 'E',
             'jurors': [('Gideon', 'Choo'), ('Leszek', 'Gladczuk'), ('Hong', 'Jung'), ('Narit', 'Triamnak')],
             'chair': ('Susan', 'Napier')},
            {'room': 'F',
             'jurors': [('Jing', 'Chen'), ('Timotheus', 'Hell'), ('Assen', 'Kyuldjiev'), ('Lidia', 'Šarić')],
             'chair': ('Florian', 'Ostermaier')},
            {'room': 'G',
             'jurors': [('Mihály', 'Hömöstrei'), ('Peter', 'Jenei'), ('Tomas', 'Opatrny'), ('Feng', 'Song')],
             'chair': ('František', 'Kundracik')},
            {'room': 'H',
             'jurors': [('Daniel', 'Keller'), ('Stanislav', 'Panos'), ('Martin', 'Schnedlitz'), ('Farida', 'Tahir')],
             'chair': ('Felicia', 'Ullstad')},
            {'room': 'I',
             'jurors': [('Ojan', 'Khatib-Damavandi'), ('Dagmar', 'Panosova'), ('Grigol', 'Peradze'), ('Ye', 'Yeo')],
             'chair': ('Ulrike', 'Regner')}
        ]
    },
    Template.TEAMROUND : {
        'round_id': 43,
        'round': 1,
        'fights': [{
             'room': 'A',
             'reporter': "United Kingdom",
             'opponent': "United States",
             'reviewer': "Germany"},
            {'room': 'B',
             'reporter': "United Kingdom",
             'opponent': "United States",
             'reviewer': "Germany"},
            {'room': 'C',
             'reporter': "United Kingdom",
             'opponent': "United States",
             'reviewer': "Germany"},
            {'room': 'D',
             'reporter': "United Kingdom",
             'opponent': "United States",
             'reviewer': "Germany"},
            {'room': 'E',
             'reporter': "United Kingdom",
             'opponent': "United States",
             'reviewer': "Germany",
             'observer': "Iran"},
            {'room': 'F',
             'reporter': "United Kingdom",
             'opponent': "United States",
             'reviewer': "Germany",},
        ]
    },
    Template.PERSONS: {
        "persons":[
            {"first_name":"Felix",
              "last_name":"Engelmann",
              "team":None,
              "email":"my@house.org",
              "roles":["Student"]},
            {"first_name": "Michael",
              "last_name": "Steck",
              "team": "Germany",
              "email": "your@house.org",
              "roles": ["EC Member"]},
        ]
    },
    Template.REGISTRATION:
    {
        "persons": [
            {
                "data": [
                    {
                        "list": [
                            "Changi (SIN)",
                            "City Airport"
                        ],
                        "needed": True,
                        "optional": False,
                        "required": True,
                        "value": None
                    },
                    {
                        "needed": True,
                        "optional": False,
                        "required": True,
                        "value": "2018-07-01 06:00:00+00:00"
                    },
                    {
                        "needed": True,
                        "optional": False,
                        "required": True,
                        "value": "Small"
                    },
                    {
                        "needed": True,
                        "optional": False,
                        "required": True,
                        "value": ""
                    },
                    {
                        "needed": True,
                        "optional": True,
                        "required": False,
                        "value": "3"
                    },
                    {
                        "needed": True,
                        "optional": False,
                        "required": True,
                        "value": "2018-02-28"
                    },
                    {
                        "needed": True,
                        "optional": False,
                        "required": True,
                        "value": "blubb"
                    },
                    {
                        "needed": True,
                        "optional": False,
                        "required": True,
                        "value": "male"
                    },
                    {
                        "needed": True,
                        "optional": True,
                        "required": False,
                        "value": ""
                    },
                    {
                        "needed": True,
                        "optional": True,
                        "required": False,
                        "value": "King II K."
                    },
                    {
                        "needed": True,
                        "optional": False,
                        "required": True,
                        "value": "2018-02-21 21:43:00+00:00"
                    },
                    {
                        "needed": True,
                        "optional": False,
                        "required": True,
                        "value": "False"
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "image": {
                            "id": 179,
                            "url": "50jahreuulm_9EhYn3J.jpg"
                        },
                        "needed": True,
                        "optional": False,
                        "required": True,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    }
                ],
                "email": "fe-iyptcc-localhost-root@nlogn.org",
                "first_name": "Root",
                "last_name": "van Engelmann",
                "team": [
                    ("Austria","Team Leader"),
                    ("Brazil","Member"),
                ],
                "roles":["Student", "Team Manager"]
            },
            {
                "data": [
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    },
                    {
                        "needed": False,
                        "optional": False,
                        "required": False,
                        "value": None
                    }
                ],
                "email": "fe-cc-test1@nlogn.org",
                "first_name": "Felix One",
                "last_name": "Engelmann",
                "team": [
                    ("Australia","Team Leader")
                ],
                "roles": ["Team Leader", "Juror"]

            }
        ],
        "properties": [
            "Pickup",
            "Arrival Time",
            "Single Choice",
            "color",
            "Ponies",
            "Date of Birth",
            "Remarks",
            "Sex",
            "Preferred Name",
            "Preferred Name (short)",
            "Departure Time",
            "Attend IOC",
            "Conflicting Origins",
            "Passport",
            "Nationality",
            "AGB",
            "CV",
            "Upgrade Single room"
        ]
    }
}
