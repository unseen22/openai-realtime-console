from brain.embedder import Embedder

def test_embedder():
    embedder = Embedder()
    
    print("Testing single text embedding...")
    text = "This is a test memory to check if the embedder is working correctly."
    try:
        vector = embedder.embed_memory(text)
        print(f"\nVector details:")
        print(f"Length: {len(vector)}")
        print(f"First few values: {vector[:5]}")
        print(f"Last few values: {vector[-5:]}")
        print(f"Non-zero elements: {sum(1 for x in vector if x != 0)}")
    except Exception as e:
        print(f"Error testing embedder: {e}")

if __name__ == "__main__":
    test_embedder() 