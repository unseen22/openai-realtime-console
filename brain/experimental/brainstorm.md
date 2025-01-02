# Memory Structure and Experience Tracking Brainstorm

## Core Concepts

### 1. Memory Node Structure [Partially Implemented]
- Each experience/memory as a node ✓
- Properties:
  - Timestamp ✓
  - Type (activity, conversation, emotion, preference) ✓
  - Content ✓
  - Importance weight ✓
  - Emotional impact score [TODO]
  - Related concepts/tags [TODO]

### 2. Memory Trees and Relations [Partially Implemented]
- Hierarchical Organization:
  - Basic temporal and semantic relationships implemented ✓
  - Advanced relationship types (emotional, causal) [TODO]
  ```
  Activities
  ├── Music [TODO]
  │   ├── Listened Songs
  │   ├── Favorite Genres
  │   └── Music Moods
  ├── Hobbies [TODO]
  └── Daily Routines [TODO]
  ```

### 3. Experience and Activity Tracking [Partially Implemented]
- Recent activities log ✓
- Activity Categories and Types [TODO]
  - Categorization of activities
  - Activity type concepts
  - Activity-type relationships
- Preference System [TODO]
  - Preference nodes with strength scores
  - Category-based preference organization
  - Preference evolution over time
- Emotional Response Tracking [TODO]
  - Emotion nodes linked to activities
  - Emotional intensity scoring
  - Cause-effect relationships
- Habit Formation [TODO]
  - Activity frequency tracking
  - Pattern recognition in activities
  - Preference strength based on repetition
  - Activity scheduling based on preferences

### 4. Self-Reflection Mechanism [Partially Implemented]
- Periodic analysis of recent experiences ✓
- Pattern recognition in activities [TODO]
- Preference evolution tracking [TODO]
- Memory consolidation process [TODO]

## Implementation Ideas

### Memory Storage Structure [Implemented ✓]
```python
class Memory:
    id: str
    timestamp: datetime
    type: str  # "activity", "preference", "emotion", "concept"
    content: dict
    vector: List[float]
    importance: float
    emotional_impact: float  # -1.0 to 1.0
    tags: Set[str]
    relationships: Dict[str, float]
    metadata: Dict  # For activity-specific data
```

### Activity Logger Structure [TODO]
```python
class ActivityLogger:
    def log_activity(
        activity: str,
        activity_type: str,
        importance: float,
        emotional_valence: float,
        metadata: Dict,
        tags: List[str]
    ) -> Memory

    def log_emotion(
        emotion: str,
        intensity: float,
        cause: str,
        metadata: Dict
    ) -> Memory

    def log_preference(
        preference: str,
        strength: float,
        category: str,
        metadata: Dict
    ) -> Memory
```

### Key Features to Implement [Priority Order]
1. **Activity and Emotion Tracking** [HIGH PRIORITY]
   - Implement ActivityLogger class
   - Add emotion tracking with cause-effect
   - Create preference tracking system
   - Add activity type categorization

2. **Emotional Impact and Tags** [HIGH PRIORITY]
   - Add emotional_impact field to Memory nodes
   - Implement tagging system
   - Add emotional analysis to memory creation

3. **Advanced Memory Relations** [MEDIUM PRIORITY]
   - Implement emotional relationships
   - Add causal relationship detection
   - Enhance semantic relationship weights

4. **Experience Analysis** [MEDIUM PRIORITY]
   - Implement frequency tracking
   - Add preference strength calculation
   - Build activity pattern detection

5. **Memory Consolidation** [LOW PRIORITY]
   - Design memory pruning strategy
   - Implement importance recalculation
   - Add long-term memory storage

## Next Steps [Concrete Actions]
1. Create ActivityLogger class with core tracking functions
2. Add activity type and category system
3. Implement preference tracking and evolution
4. Add emotional response tracking
5. Develop habit formation tracking
6. Build experience tracking analytics

## Questions to Address [Current Focus]
- How to implement emotional scoring for memories?
- What activity categories should we define initially?
- How to measure and update preference strength over time?
- What triggers should update emotional impact?
- How to detect and reinforce habits?
- How to balance preference strength with emotional impact?

## Topic Categorization and Memory Organization

### Topic Node Structure
```python
class TopicNode:
    id: str
    name: str
    type: str  # "category", "subcategory", "topic"
    parent_id: Optional[str]
    metadata: Dict[str, Any]
    importance: float
    related_topics: List[str]
```

### Core Topic Categories
1. **Entertainment & Media**
   - Music
     - Genres
     - Artists
     - Favorite Songs
     - Listening History
   - Videos
     - Movies
     - TV Shows
     - YouTube Content
     - Creators
   - Games
     - Video Games
     - Board Games
     - Game Categories

2. **Hobbies & Activities**
   - Creative Activities
     - Writing
     - Art
     - Crafts
   - Physical Activities
     - Sports
     - Exercise
     - Dance
   - Learning
     - Courses
     - Books
     - Skills

3. **Social & Relationships**
   - Friends
   - Family
   - Professional
   - Communities
   - Online Interactions

4. **Daily Life**
   - Routines
   - Places
   - Food & Dining
   - Shopping
   - Work/Study

### Implementation Strategy

#### 1. Neo4j Schema Extensions
```cypher
// Topic node structure
CREATE (t:Topic {
    id: "unique_id",
    name: "topic_name",
    type: "category|subcategory|topic",
    importance: 0.8,
    created_at: timestamp()
})

// Topic hierarchy relationships
CREATE (parent:Topic)-[:CONTAINS]->(child:Topic)

// Memory categorization
CREATE (memory:Memory)-[:BELONGS_TO]->(topic:Topic)

// Topic relationships
CREATE (topic1:Topic)-[:RELATED_TO {strength: 0.7}]->(topic2:Topic)
```

#### 2. Memory Categorization Process
1. **Automatic Topic Detection**
   ```python
   def categorize_memory(content: str) -> List[str]:
       """
       Analyze memory content and return relevant topic IDs
       Uses LLM to detect topics from content
       """
       prompt = f"""
       Given this memory content: "{content}"
       Identify relevant topics from our hierarchy.
       Consider:
       - Main category (Entertainment, Hobbies, Social, Daily)
       - Specific subcategories
       - Related topics
       Return as JSON list of topic paths.
       """
       # Process with LLM and return topic IDs
   ```

2. **Topic Relationship Strength**
   ```python
   def calculate_topic_relationship(topic1: str, topic2: str) -> float:
       """
       Calculate relationship strength between topics based on:
       - Shared memories
       - Temporal proximity
       - Semantic similarity
       - User interaction patterns
       """
   ```

3. **Memory Organization**
   ```python
   def organize_memory(memory: Memory, topics: List[str]):
       """
       1. Create BELONGS_TO relationships
       2. Update topic importance
       3. Strengthen topic relationships
       4. Create new topics if needed
       """
   ```

### Query Patterns

1. **Topic-Based Memory Retrieval**
   ```cypher
   MATCH (t:Topic {name: "Music"})<-[:BELONGS_TO]-(m:Memory)
   RETURN m ORDER BY m.timestamp DESC
   ```

2. **Related Topics Discovery**
   ```cypher
   MATCH (t:Topic {name: "Gaming"})-[:RELATED_TO]->(related:Topic)
   RETURN related, relationship.strength
   ORDER BY relationship.strength DESC
   ```

3. **Topic Hierarchy Navigation**
   ```cypher
   MATCH path = (root:Topic {type: "category"})-[:CONTAINS*]->(leaf:Topic)
   WHERE root.name = "Entertainment"
   RETURN path
   ```

### Integration with Current System

1. **Memory Creation Extension**
   ```python
   def create_memory(self, content: str):
       # Create memory node as before
       memory = self._create_memory_node(content)
       
       # Detect and link topics
       topics = self._detect_topics(content)
       self._link_memory_to_topics(memory, topics)
       
       # Update topic relationships
       self._update_topic_relationships(topics)
   ```

2. **Topic Management**
   ```python
   def manage_topics(self):
       # Periodic topic hierarchy maintenance
       # Merge similar topics
       # Prune unused topics
       # Update relationship strengths
   ```

### Next Implementation Steps
1. Create basic topic hierarchy in Neo4j
2. Implement topic detection using LLM
3. Extend Memory class with topic relationships
4. Add topic-based query methods
5. Implement automatic topic organization
6. Create topic management utilities

### Questions to Consider
- How to handle emerging topics not in the hierarchy?
- When to create new topic categories vs. using existing ones?
- How to balance automatic vs. manual topic organization?
- How to handle topic drift over time?
- What metrics to use for topic relationship strength?
