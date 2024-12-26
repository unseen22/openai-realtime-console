from typing import List, Dict, Optional, Set
from datetime import datetime
from .memory_node import MemoryNode, NodeType, RelationType
import networkx as nx

class MemoryGraph:
    def __init__(self):
        self.nodes: Dict[str, MemoryNode] = {}
        self.graph = nx.DiGraph()  # Directed graph for relationships
        print("\n📊 Initializing MemoryGraph")
        
    def add_node(self, node: MemoryNode) -> None:
        """Add a new memory node to the graph"""
        print(f"\n➕ Adding node to graph: {node.node_id}")
        print(f"  Type: {node.node_type.value}")
        print(f"  Content: {node.content[:50]}...")
        
        self.nodes[node.node_id] = node
        self.graph.add_node(node.node_id)
        
        # Add edges for all relations
        for target_id, relation in node.relations.items():
            if target_id in self.nodes:
                print(f"  Adding edge: {node.node_id} -> {target_id}")
                print(f"    Type: {relation.relation_type.value}")
                print(f"    Strength: {relation.strength:.2f}")
                self.graph.add_edge(
                    node.node_id,
                    target_id,
                    relation_type=relation.relation_type,
                    strength=relation.strength
                )
    
    def remove_node(self, node_id: str) -> None:
        """Remove a node and all its relations"""
        if node_id in self.nodes:
            print(f"\n❌ Removing node: {node_id}")
            del self.nodes[node_id]
            self.graph.remove_node(node_id)
    
    def get_node(self, node_id: str) -> Optional[MemoryNode]:
        """Get a node by its ID"""
        node = self.nodes.get(node_id)
        if node:
            print(f"\n🔍 Retrieved node: {node_id}")
            print(f"  Type: {node.node_type.value}")
            print(f"  Content: {node.content[:50]}...")
        return node
    
    def add_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType,
        strength: float = 1.0,
        context: Optional[str] = None
    ) -> None:
        """Add a relation between two nodes"""
        if source_id in self.nodes and target_id in self.nodes:
            print(f"\n🔗 Adding relation: {source_id} -> {target_id}")
            print(f"  Type: {relation_type.value}")
            print(f"  Strength: {strength:.2f}")
            
            source_node = self.nodes[source_id]
            source_node.add_relation(target_id, relation_type, strength, context)
            self.graph.add_edge(source_id, target_id, relation_type=relation_type, strength=strength)
    
    def get_related_nodes(
        self,
        node_id: str,
        relation_type: Optional[RelationType] = None,
        min_strength: float = 0.0,
        max_depth: int = 1
    ) -> List[MemoryNode]:
        """Get related nodes up to a certain depth"""
        print(f"\n🔍 Finding related nodes for: {node_id}")
        if relation_type:
            print(f"  Relation type: {relation_type.value}")
        print(f"  Min strength: {min_strength:.2f}")
        print(f"  Max depth: {max_depth}")
        
        if node_id not in self.nodes:
            print("  ❌ Node not found")
            return []
        
        related_nodes = []
        visited = set()
        
        def dfs(current_id: str, depth: int):
            if depth > max_depth or current_id in visited:
                return
            
            visited.add(current_id)
            current_node = self.nodes[current_id]
            print(f"  Visiting node: {current_id}")
            
            for target_id, relation in current_node.relations.items():
                if relation_type and relation.relation_type != relation_type:
                    continue
                if relation.strength < min_strength:
                    continue
                    
                target_node = self.nodes.get(target_id)
                if target_node and target_id not in visited:
                    print(f"    Found related node: {target_id}")
                    print(f"      Type: {target_node.node_type.value}")
                    print(f"      Content: {target_node.content[:50]}...")
                    related_nodes.append(target_node)
                    dfs(target_id, depth + 1)
        
        dfs(node_id, 0)
        print(f"  Found {len(related_nodes)} related nodes")
        return related_nodes
    
    def find_path(
        self,
        start_id: str,
        end_id: str,
        relation_types: Optional[Set[RelationType]] = None
    ) -> List[MemoryNode]:
        """Find a path between two nodes, optionally filtered by relation types"""
        print(f"\n🔍 Finding path: {start_id} -> {end_id}")
        if relation_types:
            print(f"  Relation types: {[rt.value for rt in relation_types]}")
        
        if start_id not in self.nodes or end_id not in self.nodes:
            print("  ❌ Start or end node not found")
            return []
        
        try:
            path = nx.shortest_path(self.graph, start_id, end_id)
            if relation_types:
                # Verify all edges in path have valid relation types
                for i in range(len(path) - 1):
                    edge_data = self.graph.get_edge_data(path[i], path[i + 1])
                    if edge_data["relation_type"] not in relation_types:
                        print("  ❌ Path contains invalid relation types")
                        return []
            print(f"  ✅ Found path of length {len(path)}")
            return [self.nodes[node_id] for node_id in path]
        except nx.NetworkXNoPath:
            print("  ❌ No path found")
            return []
    
    def get_nodes_by_type(self, node_type: NodeType) -> List[MemoryNode]:
        """Get all nodes of a specific type"""
        nodes = [
            node for node in self.nodes.values()
            if node.node_type == node_type
        ]
        print(f"\n🔍 Found {len(nodes)} nodes of type: {node_type.value}")
        return nodes
    
    def get_nodes_by_tag(self, tag: str) -> List[MemoryNode]:
        """Get all nodes with a specific tag"""
        nodes = [
            node for node in self.nodes.values()
            if tag in node.tags
        ]
        print(f"\n🔍 Found {len(nodes)} nodes with tag: {tag}")
        return nodes
    
    def get_most_active_nodes(self, limit: int = 10) -> List[MemoryNode]:
        """Get the most active nodes based on activation level"""
        print(f"\n🔍 Finding {limit} most active nodes")
        current_time = datetime.now()
        nodes_with_activation = [
            (node, node.calculate_activation(current_time))
            for node in self.nodes.values()
        ]
        nodes_with_activation.sort(key=lambda x: x[1], reverse=True)
        result = [node for node, _ in nodes_with_activation[:limit]]
        print(f"  Found {len(result)} active nodes")
        return result
    
    def prune_weak_relations(self, min_strength: float = 0.1) -> None:
        """Remove relations that have fallen below the minimum strength"""
        print(f"\n✂️ Pruning relations with strength < {min_strength:.2f}")
        pruned_count = 0
        for node in self.nodes.values():
            weak_relations = [
                target_id for target_id, relation in node.relations.items()
                if relation.strength < min_strength
            ]
            for target_id in weak_relations:
                print(f"  Removing weak relation: {node.node_id} -> {target_id}")
                del node.relations[target_id]
                if self.graph.has_edge(node.node_id, target_id):
                    self.graph.remove_edge(node.node_id, target_id)
                pruned_count += 1
        print(f"✅ Pruned {pruned_count} weak relations")
    
    def merge_nodes(self, source_id: str, target_id: str) -> None:
        """Merge two nodes and their relations"""
        print(f"\n🔄 Merging nodes: {source_id} -> {target_id}")
        if source_id not in self.nodes or target_id not in self.nodes:
            print("  ❌ Source or target node not found")
            return
            
        source_node = self.nodes[source_id]
        target_node = self.nodes[target_id]
        
        # Merge metadata and tags
        print("  Merging metadata and tags")
        target_node.metadata.update(source_node.metadata)
        target_node.tags.update(source_node.tags)
        
        # Merge relations
        print("  Merging relations")
        for rel_id, relation in source_node.relations.items():
            if rel_id != target_id:  # Avoid self-relations
                print(f"    Adding relation to: {rel_id}")
                target_node.add_relation(
                    rel_id,
                    relation.relation_type,
                    relation.strength,
                    relation.context
                )
        
        # Remove source node
        print("  Removing source node")
        self.remove_node(source_id)
        print("✅ Merge complete")
    
    def to_dict(self) -> dict:
        """Convert entire graph to dictionary for storage"""
        return {
            "nodes": {
                node_id: node.to_dict()
                for node_id, node in self.nodes.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MemoryGraph':
        """Create graph instance from dictionary"""
        graph = cls()
        for node_data in data["nodes"].values():
            node = MemoryNode.from_dict(node_data)
            graph.add_node(node)
        return graph 