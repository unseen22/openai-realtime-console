from datetime import datetime, timedelta
import random

FAKE_MEMORIES = [
    {
        "id": 1,
        "string": "Went to McDonald's and saw Michael Jordan. Had the best time of my life getting his autograph.",
        "timestamp": "2024-03-15T14:30:00",
        "importance": 9,
        "type": "conversation"
    },
    {
        "id": 2,
        "string": "Found a stray cat in the rain and took it home. Now we're inseparable and I named her Luna.",
        "timestamp": "2024-03-14T09:15:00",
        "importance": 7,
        "type": "conversation"
    },
    {
        "id": 3,
        "string": "Learned to play 'Wonderwall' on guitar at the beach. Everyone joined in singing and it became a spontaneous party.",
        "timestamp": "2024-03-13T16:45:00",
        "importance": 6,
        "type": "conversation"
    },
    {
        "id": 4,
        "string": "Helped an elderly woman cross the street during a storm. She turned out to be a retired piano teacher and gave me free lessons.",
        "timestamp": "2024-03-12T11:20:00",
        "importance": 8,
        "type": "conversation"
    },
    {
        "id": 5,
        "string": "Discovered a hidden bookstore behind my apartment. The owner shares my love for science fiction and recommends amazing books.",
        "timestamp": "2024-03-11T15:10:00",
        "importance": 7,
        "type": "conversation"
    },
    {
        "id": 6,
        "string": "Made breakfast for the whole family on Sunday. The pancakes were burnt but everyone said it was the best meal ever.",
        "timestamp": "2024-03-10T08:30:00",
        "importance": 8,
        "type": "conversation"
    },
    {
        "id": 7,
        "string": "Went skydiving for the first time yesterday. The instructor was so calm it made the whole experience magical.",
        "timestamp": "2024-03-09T13:45:00",
        "importance": 9,
        "type": "conversation"
    },
    {
        "id": 8,
        "string": "Plant I've been caring for finally bloomed. The purple flowers made my whole room smell like lavender.",
        "timestamp": "2024-03-08T17:20:00",
        "importance": 5,
        "type": "conversation"
    },
    {
        "id": 9,
        "string": "Random stranger paid for my coffee this morning. Decided to pay it forward and bought coffee for the person behind me.",
        "timestamp": "2024-03-07T07:30:00",
        "importance": 6,
        "type": "conversation"
    },
    {
        "id": 10,
        "string": "Fixed my neighbor's bike and taught their kid how to ride. The look of joy on their faces was priceless.",
        "timestamp": "2024-03-06T16:15:00",
        "importance": 7,
        "type": "conversation"
    },
    {
        "id": 11,
        "string": "Saw a double rainbow after the storm today. The entire neighborhood came out to take pictures together.",
        "timestamp": "2024-03-05T18:30:00",
        "importance": 6,
        "type": "conversation"
    },
    {
        "id": 12,
        "string": "Won first place in the local chess tournament. My grandfather would have been so proud of me.",
        "timestamp": "2024-03-04T14:20:00",
        "importance": 8,
        "type": "conversation"
    },
    {
        "id": 13,
        "string": "Cooked my grandmother's secret recipe for the first time. The taste brought back so many childhood memories.",
        "timestamp": "2024-03-03T19:45:00",
        "importance": 8,
        "type": "conversation"
    },
    {
        "id": 14,
        "string": "Found my old diary from high school in the attic. Spent hours laughing at my teenage thoughts and dreams.",
        "timestamp": "2024-03-02T12:10:00",
        "importance": 7,
        "type": "conversation"
    },
    {
        "id": 15,
        "string": "Rescued a baby bird that fell from its nest. Watched from my window as its mother came back for it.",
        "timestamp": "2024-03-01T15:30:00",
        "importance": 7,
        "type": "conversation"
    },
    {
        "id": 16,
        "string": "Learned to make sushi from my Japanese neighbor. We ended up sharing stories about our cultures all evening.",
        "timestamp": "2024-02-29T17:20:00",
        "importance": 8,
        "type": "conversation"
    },
    {
        "id": 17,
        "string": "Finished my first marathon today. The stranger who ran beside me for the last mile became a good friend.",
        "timestamp": "2024-02-28T11:45:00",
        "importance": 9,
        "type": "conversation"
    },
    {
        "id": 18,
        "string": "Started a community garden in our neighborhood. Now everyone brings vegetables to share at Sunday potlucks.",
        "timestamp": "2024-02-27T10:15:00",
        "importance": 8,
        "type": "conversation"
    },
    {
        "id": 19,
        "string": "Taught my grandma how to use video calls. She cried when she saw her great-grandchildren for the first time.",
        "timestamp": "2024-02-26T13:30:00",
        "importance": 9,
        "type": "conversation"
    },
    {
        "id": 20,
        "string": "Wrote a song and performed it at the local cafe. A music producer happened to be there and loved it.",
        "timestamp": "2024-02-25T20:00:00",
        "importance": 8,
        "type": "conversation"
    }
]
def get_fake_memories(limit: int = None, min_importance: int = None):
    """Get fake memories with optional filtering"""
    import random
    
    filtered_memories = FAKE_MEMORIES
    
    if min_importance is not None:
        filtered_memories = [m for m in filtered_memories if m["importance"] >= min_importance]



    random_memory = [random.choice(filtered_memories)]
    print(random_memory)    
    # Always return just 1 random memory
    return random_memory