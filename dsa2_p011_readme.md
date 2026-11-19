# DSA2-P011: Search Autocomplete Engine

A **Search Autocomplete Engine** built for Data Structures & Algorithms (`DSA2-P011`). It indexes **5,600+ weighted words and contacts**, supports dynamic `INSERT`, `UPDATE`, and `DELETE` operations with safe dead-branch pruning, returns either **Top-$K$ ranked suggestions** or **All prefix matches**, tracks query latency, and displays live **prefix traversal** and subtree branches in a web interface.

---

## Key Features

* **Large-Scale Dataset:** Preloads **5,600** words and contacts with frequency weights from `dataset.txt` (exceeding the 5,000-record requirement).
* **Fast Prefix Lookup:** Navigates prefixes in $O(P)$ time independent of dataset size $N$.
* **Top-$K$ & All-Matches Modes:** Switches seamlessly between bounded Min-Heap Top-$K$ ranking and full sorted subtree retrieval.
* **Dynamic CRUD with Pruning:** Supports inserting new entries, updating weights/priorities, and deleting entries while freeing orphaned Trie branches via `passCount`.
* **Live Traversal & Visualization:** Displays the exact path walked from `ROOT` along each character of the prefix, next-character branch metadata, match counts, and query latency.
* **Cross-Platform Execution:** Runs natively with compiled C++17 (`autocomplete_engine.cpp`) and automatically falls back to an identical Python implementation (`trie_engine.py`) in restricted environments where `g++` is unavailable.

---

## Project Architecture

```text
DSA2-P011-Cpp-Python/
├── autocomplete_engine.cpp   # C++17 Trie + Min-Heap Top-K + passCount pruning engine
├── trie_engine.py            # Python drop-in fallback implementing the exact same protocol
├── generate_dataset.py       # Generates 5,600+ weighted words & contacts into dataset.txt
├── dataset.txt               # Tab-separated dataset (<weight>\t<word/contact>)
├── app.py                    # Flask bridge + live search UI & Trie traversal visualizer
└── README.md                 # Project documentation
```

### Engine Command Protocol (`stdin` / `stdout`)

Both `autocomplete_engine.cpp` and `trie_engine.py` communicate with `app.py` over a persistent line-delimited protocol returning JSON responses:

* `INSERT <weight> <word>` — Inserts a record or increments an existing record's weight.
* `UPDATE <weight> <word>` — Updates the priority weight of an existing record.
* `DELETE <word>` — Removes a record and prunes unused branches (`prunedNodes`).
* `SEARCH <mode:topk|all> <k> <prefix>` — Returns traversal steps, match count, next branches, and ranked results.
* `QUIT` — Cleanly terminates the engine process.

---

## Data Structures & Complexity Analysis

Let $N$ be total indexed records ($N \ge 5,600$), $L$ be the length of a word/contact, $P$ be the length of the query prefix, $M$ be the number of matching entries inside the prefix subtree, $S$ be the number of dead nodes pruned during deletion, and $K$ be the requested Top-$K$ count.

| Operation / Component | Time Complexity | Space Complexity | Implementation Details |
| :--- | :--- | :--- | :--- |
| **Insert** | $O(L)$ | $O(L)$ worst-case | Walks/creates `TrieNode` edges using hash-map children and increments `passCount`. |
| **Update Weight** | $O(L)$ | $O(1)$ | Locates the terminal node in $O(L)$ and updates its `weight`. |
| **Delete + Pruning** | $O(L + S)$ | $O(1)$ auxiliary | Decrements `passCount`; detaches and frees the branch immediately when `passCount == 0`. |
| **Prefix Traversal** | $O(P)$ | $O(P)$ | Follows prefix characters from `ROOT`, recording node stats at every step. |
| **Top-$K$ Suggestions** | $O(M \log K)$ | $O(K)$ heap | Runs DFS over the prefix subtree and maintains a fixed-capacity Min-Heap (evicting the weakest candidate). |
| **All Matches Mode** | $O(M \log M)$ | $O(M)$ | Collects all $M$ matches in the subtree and sorts by weight descending, then lexicographically. |
| **Trie Storage** | — | $O(N \cdot L)$ worst-case | Shared prefixes compress memory well below raw character count. |

### Why Trie + Bounded Min-Heap?

* **Versus Hash Map:** A Hash Map supports $O(1)$ exact lookup but cannot enumerate prefix matches without scanning all $N$ keys.
* **Versus Sorted Array + Binary Search:** Binary search finds prefixes in $O(P \log N)$ but incurs $O(N)$ shifting overhead on dynamic insertions and deletions.
* **Bounded Min-Heap vs. Full Sort:** Keeping only the top $K$ items in a Min-Heap bounds auxiliary heap space to $O(K)$ and reduces ranking overhead to $O(M \log K)$.

---

## How to Run

### Option 1: Windows (PowerShell with `g++`)

```powershell
g++ -std=c++17 -O2 autocomplete_engine.cpp -o autocomplete_engine.exe
python generate_dataset.py
pip install flask
python app.py
```

Open **`http://127.0.0.1:5000`** in your browser.

### Option 2: Linux / byteXL Nimbus (Bash)

If `g++` is available in your container, compile the C++ engine first:

```bash
g++ -std=c++17 -O2 autocomplete_engine.cpp -o autocomplete_engine
```

Then generate the dataset, install Flask, and start the web app (`app.py` automatically uses `trie_engine.py` if no compiled C++ binary is present):

```bash
python3 generate_dataset.py
pip install --user flask
python3 app.py
```

Open port **`5000`** via the workspace **Ports / Preview** panel (or visit `http://127.0.0.1:5000` locally).

---

## Quick Verification Checklist

1. **Scale Check:** Verify **5,600** records load on startup and display in the top stats bar.
2. **Prefix Search:** Type `app`, `aarav`, or `data` and confirm live suggestions, total match count, and prefix traversal update immediately.
3. **Top-$K$ vs. All Matches:** Toggle between **Top-$K$ Ranked** (adjusting $K$) and **All Matches** to confirm ranking and count behavior.
4. **Dynamic CRUD & Pruning:** Insert a new unique word, update its weight, then delete it and confirm `prunedNodes` is greater than zero and total `Trie Nodes` decreases.
5. **Missing Prefix Handling:** Search an invalid prefix like `xyz` and confirm partial traversal stops cleanly at the missing character with zero matches.