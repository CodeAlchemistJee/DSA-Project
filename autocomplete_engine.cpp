#include <algorithm>
#include <cctype>
#include <iostream>
#include <queue>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

using namespace std;

struct MatchItem {
    string word;
    int weight;
};

struct StepInfo {
    string label;
    int passCount;
    bool isEnd;
    int childCount;
};

struct BranchInfo {
    char ch;
    int passCount;
    bool isEnd;
    int childCount;
};

// Min-heap comparator: keeps the K strongest items by putting the "worst" at top()
struct WorseMatch {
    bool operator()(const MatchItem& a, const MatchItem& b) const {
        if (a.weight != b.weight) return a.weight > b.weight; // smaller weight = worse
        return a.word < b.word; // lexicographically later = worse on tie
    }
};

struct TrieNode {
    char ch;
    unordered_map<char, TrieNode*> children;
    bool isEnd = false;
    string originalWord = "";
    int weight = 0;
    int passCount = 0;

    explicit TrieNode(char c = '#') : ch(c) {}
};

class AutocompleteEngine {
private:
    TrieNode* root;
    long long totalRecords = 0;
    long long totalNodes = 1;

    static string normalize(const string& s) {
        string out;
        out.reserve(s.size());
        for (unsigned char c : s) {
            if (!isspace(c)) {
                out.push_back(static_cast<char>(tolower(c)));
            }
        }
        return out;
    }

    static string trim(const string& s) {
        size_t start = 0;
        while (start < s.size() && isspace(static_cast<unsigned char>(s[start]))) ++start;
        size_t end = s.size();
        while (end > start && isspace(static_cast<unsigned char>(s[end - 1]))) --end;
        return s.substr(start, end - start);
    }

    TrieNode* findExactNode(const string& key) const {
        if (key.empty()) return nullptr;
        TrieNode* curr = root;
        for (char c : key) {
            auto it = curr->children.find(c);
            if (it == curr->children.end()) return nullptr;
            curr = it->second;
        }
        return curr->isEnd ? curr : nullptr;
    }

    long long countSubtree(TrieNode* node) const {
        if (!node) return 0;
        long long cnt = 1;
        for (const auto& kv : node->children) {
            cnt += countSubtree(kv.second);
        }
        return cnt;
    }

    void freeSubtree(TrieNode* node) {
        if (!node) return;
        for (const auto& kv : node->children) {
            freeSubtree(kv.second);
        }
        delete node;
    }

    void collectDfs(
        TrieNode* node,
        vector<MatchItem>& allMatches,
        priority_queue<MatchItem, vector<MatchItem>, WorseMatch>* minHeap,
        int k
    ) const {
        if (!node) return;
        if (node->isEnd) {
            MatchItem item{node->originalWord, node->weight};
            allMatches.push_back(item);
            if (minHeap != nullptr && k > 0) {
                if (static_cast<int>(minHeap->size()) < k) {
                    minHeap->push(item);
                } else if (item.weight > minHeap->top().weight ||
                          (item.weight == minHeap->top().weight && item.word < minHeap->top().word)) {
                    minHeap->pop();
                    minHeap->push(item);
                }
            }
        }

        vector<char> keys;
        keys.reserve(node->children.size());
        for (const auto& kv : node->children) keys.push_back(kv.first);
        sort(keys.begin(), keys.end());

        for (char c : keys) {
            collectDfs(node->children.at(c), allMatches, minHeap, k);
        }
    }

    static string jsonEscape(const string& s) {
        string out;
        for (char c : s) {
            if (c == '\\') out += "\\\\";
            else if (c == '"') out += "\\\"";
            else if (c == '\n') out += "\\n";
            else out.push_back(c);
        }
        return out;
    }

public:
    AutocompleteEngine() {
        root = new TrieNode('#');
    }

    ~AutocompleteEngine() {
        freeSubtree(root);
    }

    bool insertWord(const string& rawWord, int w) {
        string clean = trim(rawWord);
        string key = normalize(clean);
        if (key.empty()) return false;
        if (w < 1) w = 1;

        TrieNode* existing = findExactNode(key);
        if (existing != nullptr) {
            existing->weight += w;
            existing->originalWord = clean;
            return true;
        }

        TrieNode* curr = root;
        curr->passCount++;
        for (char c : key) {
            auto it = curr->children.find(c);
            if (it == curr->children.end()) {
                TrieNode* next = new TrieNode(c);
                curr->children[c] = next;
                ++totalNodes;
                curr = next;
            } else {
                curr = it->second;
            }
            curr->passCount++;
        }
        curr->isEnd = true;
        curr->originalWord = clean;
        curr->weight = w;
        ++totalRecords;
        return true;
    }

    bool updateWeight(const string& rawWord, int newWeight) {
        string key = normalize(rawWord);
        TrieNode* node = findExactNode(key);
        if (node == nullptr) return false;
        node->weight = max(0, newWeight);
        return true;
    }

    bool deleteWord(const string& rawWord, long long& prunedCount) {
        prunedCount = 0;
        string key = normalize(rawWord);
        TrieNode* target = findExactNode(key);
        if (target == nullptr) return false;

        TrieNode* curr = root;
        curr->passCount--;
        for (char c : key) {
            TrieNode* next = curr->children[c];
            next->passCount--;
            if (next->passCount == 0) {
                prunedCount = countSubtree(next);
                curr->children.erase(c);
                freeSubtree(next);
                totalNodes -= prunedCount;
                --totalRecords;
                return true;
            }
            curr = next;
        }

        curr->isEnd = false;
        curr->originalWord.clear();
        curr->weight = 0;
        --totalRecords;
        return true;
    }

    void printSearchJson(const string& rawPrefix, const string& mode, int k) const {
        string key = normalize(rawPrefix);
        vector<StepInfo> steps;
        steps.push_back(StepInfo{"ROOT", root->passCount, false, static_cast<int>(root->children.size())});

        TrieNode* curr = root;
        bool found = true;
        char failedChar = '\0';

        for (char c : key) {
            auto it = curr->children.find(c);
            if (it == curr->children.end()) {
                found = false;
                failedChar = c;
                break;
            }
            curr = it->second;
            steps.push_back(StepInfo{
                string(1, c),
                curr->passCount,
                curr->isEnd,
                static_cast<int>(curr->children.size())
            });
        }

        vector<MatchItem> outputItems;
        vector<BranchInfo> branches;
        long long totalMatches = 0;

        if (found) {
            vector<MatchItem> allMatches;
            priority_queue<MatchItem, vector<MatchItem>, WorseMatch> minHeap;
            bool useTopK = (mode == "topk");
            collectDfs(curr, allMatches, useTopK ? &minHeap : nullptr, k);
            totalMatches = static_cast<long long>(allMatches.size());

            if (useTopK) {
                while (!minHeap.empty()) {
                    outputItems.push_back(minHeap.top());
                    minHeap.pop();
                }
                sort(outputItems.begin(), outputItems.end(), [](const MatchItem& a, const MatchItem& b) {
                    if (a.weight != b.weight) return a.weight > b.weight;
                    return a.word < b.word;
                });
            } else {
                outputItems = move(allMatches);
                sort(outputItems.begin(), outputItems.end(), [](const MatchItem& a, const MatchItem& b) {
                    if (a.weight != b.weight) return a.weight > b.weight;
                    return a.word < b.word;
                });
            }

            vector<char> bKeys;
            bKeys.reserve(curr->children.size());
            for (const auto& kv : curr->children) bKeys.push_back(kv.first);
            sort(bKeys.begin(), bKeys.end());
            for (char c : bKeys) {
                TrieNode* child = curr->children.at(c);
                branches.push_back(BranchInfo{
                    c,
                    child->passCount,
                    child->isEnd,
                    static_cast<int>(child->children.size())
                });
            }
        }

        cout << "{\"ok\":true,\"found\":" << (found ? "true" : "false")
             << ",\"prefix\":\"" << jsonEscape(key) << "\""
             << ",\"failedAt\":\"" << (failedChar ? string(1, failedChar) : string()) << "\""
             << ",\"totalMatches\":" << totalMatches
             << ",\"totalRecords\":" << totalRecords
             << ",\"totalNodes\":" << totalNodes
             << ",\"traversal\":[";

        for (size_t i = 0; i < steps.size(); ++i) {
            if (i > 0) cout << ",";
            cout << "{\"node\":\"" << jsonEscape(steps[i].label) << "\""
                 << ",\"passCount\":" << steps[i].passCount
                 << ",\"isEnd\":" << (steps[i].isEnd ? "true" : "false")
                 << ",\"children\":" << steps[i].childCount << "}";
        }

        cout << "],\"results\":[";
        for (size_t i = 0; i < outputItems.size(); ++i) {
            if (i > 0) cout << ",";
            cout << "{\"word\":\"" << jsonEscape(outputItems[i].word) << "\""
                 << ",\"weight\":" << outputItems[i].weight << "}";
        }

        cout << "],\"branches\":[";
        for (size_t i = 0; i < branches.size(); ++i) {
            if (i > 0) cout << ",";
            cout << "{\"char\":\"" << branches[i].ch << "\""
                 << ",\"passCount\":" << branches[i].passCount
                 << ",\"isEnd\":" << (branches[i].isEnd ? "true" : "false")
                 << ",\"children\":" << branches[i].childCount << "}";
        }
        cout << "]}\n" << flush;
    }
};

// Command protocol (one command per line):
// INSERT <weight> <word>
// UPDATE <weight> <word>
// DELETE <word>
// SEARCH <mode:topk|all> <k> <prefix>
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    AutocompleteEngine engine;
    string line;

    while (getline(cin, line)) {
        if (line.empty()) continue;
        istringstream iss(line);
        string cmd;
        iss >> cmd;

        if (cmd == "INSERT") {
            int w = 1;
            iss >> w;
            string word;
            getline(iss, word);
            bool ok = engine.insertWord(word, w);
            cout << "{\"ok\":" << (ok ? "true" : "false") << ",\"op\":\"INSERT\"}\n" << flush;
        } else if (cmd == "UPDATE") {
            int w = 0;
            iss >> w;
            string word;
            getline(iss, word);
            bool ok = engine.updateWeight(word, w);
            cout << "{\"ok\":" << (ok ? "true" : "false") << ",\"op\":\"UPDATE\"}\n" << flush;
        } else if (cmd == "DELETE") {
            string word;
            getline(iss, word);
            long long pruned = 0;
            bool ok = engine.deleteWord(word, pruned);
            cout << "{\"ok\":" << (ok ? "true" : "false")
                 << ",\"op\":\"DELETE\",\"prunedNodes\":" << pruned << "}\n" << flush;
        } else if (cmd == "SEARCH") {
            string mode;
            int k = 10;
            iss >> mode >> k;
            string prefix;
            getline(iss, prefix);
            if (!prefix.empty() && prefix[0] == ' ') prefix.erase(0, 1);
            engine.printSearchJson(prefix, mode, k);
        } else if (cmd == "QUIT") {
            break;
        }
    }
    return 0;
}