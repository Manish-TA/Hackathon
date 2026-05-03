# Amazon OA Recent Questions (Jan 2026 – May 2026)

Collected from recent reports on Reddit (r/leetcode, r/csMajors) and problem trackers. All solutions are optimised C++.

---

## Q1 — Worker State Arrangements (Threshold Array)

**Problem:** Given an integer array `threshold` of size `n`, where `threshold[i]` represents the threshold value of the i-th worker. Each worker can be assigned Operating or Stalled state.

**Rules:**
1. If a worker is Operating, and total workers in Operating state < `threshold[i]`, it malfunctions.
2. If a worker is Stalled, and total workers in Operating state >= `threshold[i]`, it malfunctions.

Return the number of valid arrangements (Operating/Stalled for all `n` workers) such that no worker malfunctions.

**Constraints:** 1 ≤ n ≤ 10^5, 1 ≤ threshold[i] ≤ n

**Approach:** Sort thresholds. If `k` workers are operating, they must be the `k` workers with the smallest thresholds (after sorting). For a fixed `k`, validity requires:
- All operating workers: `threshold[i] <= k` (for i = 0..k-1)
- All stalled workers: `threshold[i] > k` (for i = k..n-1)

After sorting, just check each valid split point. O(n log n).

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> threshold(n);
    for (int i = 0; i < n; i++) cin >> threshold[i];
    
    sort(threshold.begin(), threshold.end());
    
    int count = 0;
    
    // k = 0: all stalled. Valid if threshold[0] > 0 (always true since threshold >= 1)
    if (threshold[0] > 0) count++;
    
    // k = i+1 for i in [0, n-2]
    for (int i = 0; i < n - 1; i++) {
        int k = i + 1;
        // First k workers operate: need threshold[i] <= k
        // Remaining stalled: need threshold[i+1] > k
        if (threshold[i] <= k && threshold[i + 1] > k) {
            count++;
        }
    }
    
    // k = n: all operating. Valid if threshold[n-1] <= n
    if (threshold[n - 1] <= n) count++;
    
    cout << count << endl;
    return 0;
}
```

**Complexity:** O(n log n) time, O(1) extra space.

---

## Q2 — API Throttling Mechanism

**Problem:** Given array `responseTimes` of n API requests. Repeatedly:
1. Select the request with the minimum response time (lowest index on tie).
2. Remove it and its immediate neighbours (by original index).
3. Repeat until empty.

Return the sum of all selected minimums.

**Constraints:** 3 ≤ n ≤ 2×10^5, 1 ≤ responseTimes[i] ≤ 10^5

**Approach:** Min-heap (priority queue) + boolean removed array. O(n log n).

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> rt(n);
    for (int i = 0; i < n; i++) cin >> rt[i];

    vector<bool> removed(n, false);
    // {value, index} — min-heap naturally picks lowest value, lowest index on tie
    priority_queue<pair<int,int>, vector<pair<int,int>>, greater<>> pq;
    for (int i = 0; i < n; i++) pq.push({rt[i], i});

    long long total = 0;
    while (!pq.empty()) {
        auto [val, idx] = pq.top();
        pq.pop();
        if (removed[idx]) continue;
        
        total += val;
        removed[idx] = true;
        if (idx > 0) removed[idx - 1] = true;
        if (idx < n - 1) removed[idx + 1] = true;
    }

    cout << total << endl;
    return 0;
}
```

**Complexity:** O(n log n) time, O(n) space.

---

## Q3 — Minimum Time to Sort Binary String

**Problem:** Given binary string `key`, sort it (all 0s before 1s) using minimum cost:
- Swap two consecutive elements: cost = 10^12 picoseconds
- Delete any character: cost = 10^12 + 1 picoseconds

Return minimum total time.

**Constraints:** 1 ≤ |key| ≤ 2×10^5

**Approach:** 3-state DP. Swapping a '0' past 1 one (cost 10^12) is cheaper than deleting (10^12+1), but past 2+ ones, deletion wins.

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    string key;
    cin >> key;

    const long long S = 1000000000000LL;  // swap cost
    const long long D = 1000000000001LL;  // delete cost
    const long long INF = 2e18;

    // dp0: 0 ones before current position
    // dp1: exactly 1 one before current position
    // dp2: 2+ ones before current position
    long long dp0 = 0, dp1 = INF, dp2 = INF;

    for (char c : key) {
        if (c == '0') {
            // In state 0: keep 0, free
            // In state 1: swap past 1 one, cost S
            // In state 2: delete the 0, cost D
            dp2 += D;
            dp1 += S;
            // dp0 unchanged
        } else {
            // c == '1'
            long long new0 = dp0 + D;           // delete this 1
            long long new1 = min(dp0, dp1 + D); // enter from state 0 (keep 1), or delete in state 1
            long long new2 = min(dp1, dp2);     // enter from state 1 (keep 1), or stay in state 2
            dp0 = new0;
            dp1 = new1;
            dp2 = new2;
        }
    }

    cout << min({dp0, dp1, dp2}) << endl;
    return 0;
}
```

**Complexity:** O(n) time, O(1) space.

---

## Q4 — Use Minimum Tokens (Warehouse Shipment)

**Problem:** Amazon operates `n` warehouses with capacities `warehouse[i]`. For each of `q` shipments with `(needMain, needBackup)`:
- Pick one warehouse as the main. Cost = max(0, needMain - warehouse[selected]).
- Remaining warehouses must have total capacity >= needBackup. Cost = max(0, needBackup - (totalSum - warehouse[selected])).
- Total tokens = sum of both costs. Minimize over all warehouse choices.

**Constraints:** 2 ≤ n ≤ 10^5, 1 ≤ q ≤ 10^5, values up to 10^9/10^15

**Approach:** Sort warehouses. For a query, binary search for the first capacity >= needMain. Only check that index and its predecessor (the two candidates at the boundary minimize the tradeoff). O((n + q) log n).

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, q;
    cin >> n >> q;
    
    vector<long long> warehouse(n);
    long long S = 0;
    for (int i = 0; i < n; i++) {
        cin >> warehouse[i];
        S += warehouse[i];
    }
    
    sort(warehouse.begin(), warehouse.end());
    
    while (q--) {
        long long needMain, needBackup;
        cin >> needMain >> needBackup;
        
        long long ans = LLONG_MAX;
        
        // Binary search: first warehouse with capacity >= needMain
        int pos = lower_bound(warehouse.begin(), warehouse.end(), needMain) - warehouse.begin();
        
        // Check candidates: pos and pos-1
        auto cost = [&](int idx) -> long long {
            if (idx < 0 || idx >= n) return LLONG_MAX;
            long long c = warehouse[idx];
            long long mainCost = max(0LL, needMain - c);
            long long backupCap = S - c;
            long long backupCost = max(0LL, needBackup - backupCap);
            return mainCost + backupCost;
        };
        
        ans = min(ans, cost(pos));
        ans = min(ans, cost(pos - 1));
        
        cout << ans << "\n";
    }
    
    return 0;
}
```

**Complexity:** O(n log n + q log n) time, O(n) space.

---

## Q5 — Split Prefix Suffix (Shared Categories)

**Problem:** Given string `categories` of lowercase letters and integer `k`, find the number of ways to split it into two non-empty contiguous parts (prefix and suffix) such that the number of distinct characters appearing in **both** parts is > `k`.

**Constraints:** 1 ≤ |categories| ≤ 10^5, 0 ≤ k ≤ 26

**Approach:** Maintain prefix presence (boolean) and suffix frequency. Slide split from left to right, updating shared count in O(1) per step (only 26 possible chars). Total O(n).

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    string s;
    int k;
    cin >> s >> k;
    int n = s.size();
    
    // suffix frequency
    int suffFreq[26] = {};
    for (char c : s) suffFreq[c - 'a']++;
    
    bool prefPresent[26] = {};
    int shared = 0;
    int answer = 0;
    
    // split after index i: prefix = s[0..i], suffix = s[i+1..n-1]
    for (int i = 0; i < n - 1; i++) {
        int ch = s[i] - 'a';
        
        // Move s[i] from suffix to prefix
        suffFreq[ch]--;
        
        if (!prefPresent[ch]) {
            prefPresent[ch] = true;
            // newly in prefix; check if still in suffix
            if (suffFreq[ch] > 0) shared++;
        } else {
            // already in prefix; check if just left suffix
            if (suffFreq[ch] == 0) shared--;
        }
        
        if (shared > k) answer++;
    }
    
    cout << answer << endl;
    return 0;
}
```

**Complexity:** O(n) time, O(1) space.

---

## Q6 — Find Security Level (Subarray Sum % k == Length)

**Problem:** Given array `pid` of n integers and integer `k`, count the number of subarrays where `(sum of subarray) % k == length of subarray`.

**Constraints:** 1 ≤ n ≤ 10^5, 1 ≤ k ≤ 10^5

**Approach:** Algebraic trick. For subarray [l, r): `(P[r] - P[l]) % k == r - l` rearranges to `(P[r] - r) % k == (P[l] - l) % k`. Use hashmap to count prefix key frequencies. O(n).

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, k;
    cin >> n >> k;
    vector<int> pid(n);
    for (int i = 0; i < n; i++) cin >> pid[i];
    
    unordered_map<int, long long> freq;
    long long prefix = 0;
    long long answer = 0;
    
    // key for index 0 (empty prefix)
    int key0 = ((0 - 0) % k + k) % k;
    freq[key0]++;
    
    for (int i = 0; i < n; i++) {
        prefix += pid[i];
        int key = (int)(((prefix - (i + 1)) % k + k) % k);
        answer += freq[key];
        freq[key]++;
    }
    
    cout << answer << endl;
    return 0;
}
```

**Complexity:** O(n) time, O(n) space.

---

## Q7 — Minimum Difficulty of Job Schedule

**Problem:** You have `n` jobs with difficulty `jobDifficulty[i]` (must be done in order) and `d` days. Each day you must do at least one job. The difficulty of a day is the max difficulty job done that day. Minimize the sum of daily difficulties.

**Constraints:** 1 ≤ n ≤ 300, 1 ≤ d ≤ 10, 1 ≤ jobDifficulty[i] ≤ 1000

**Approach:** DP with monotonic stack optimization, or straightforward O(n^2 * d) DP.

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, d;
    cin >> n >> d;
    vector<int> job(n);
    for (int i = 0; i < n; i++) cin >> job[i];
    
    if (n < d) { cout << -1; return 0; }
    
    const int INF = 1e9;
    // dp[i][j] = min total difficulty using first i jobs in j days
    vector<vector<int>> dp(n + 1, vector<int>(d + 1, INF));
    dp[0][0] = 0;
    
    for (int day = 1; day <= d; day++) {
        for (int i = day; i <= n; i++) {
            int maxD = 0;
            for (int j = i; j >= day; j--) {
                maxD = max(maxD, job[j - 1]);
                if (dp[j - 1][day - 1] != INF) {
                    dp[i][day] = min(dp[i][day], dp[j - 1][day - 1] + maxD);
                }
            }
        }
    }
    
    cout << dp[n][d] << endl;
    return 0;
}
```

**Complexity:** O(n^2 * d) time, O(n * d) space.

---

## Q8 — Optimal Utilization (Two Sum Closest to Target)

**Problem:** Given two lists `a` and `b` of pairs (id, value), find pairs (one from each list) whose values sum up to closest to (but not exceeding) a target. Return all such pairs (by id).

**Constraints:** 1 ≤ |a|, |b| ≤ 10^5, values up to 10^9

**Approach:** Sort both by value. Two-pointer from left of `a` and right of `b`. Track best sum ≤ target.

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int target;
    cin >> target;
    
    int m, n;
    cin >> m;
    vector<pair<int,int>> a(m); // {value, id}
    for (int i = 0; i < m; i++) {
        int id, val;
        cin >> id >> val;
        a[i] = {val, id};
    }
    cin >> n;
    vector<pair<int,int>> b(n);
    for (int i = 0; i < n; i++) {
        int id, val;
        cin >> id >> val;
        b[i] = {val, id};
    }
    
    sort(a.begin(), a.end());
    sort(b.begin(), b.end());
    
    int i = 0, j = n - 1;
    long long best = -1;
    vector<pair<int,int>> result;
    
    while (i < m && j >= 0) {
        long long sum = (long long)a[i].first + b[j].first;
        if (sum <= target) {
            if (sum > best) {
                best = sum;
                result.clear();
            }
            if (sum == best) {
                // Also check duplicates in b
                int jj = j;
                while (jj >= 0 && (long long)a[i].first + b[jj].first == best) {
                    result.push_back({a[i].second, b[jj].second});
                    jj--;
                }
            }
            i++;
        } else {
            j--;
        }
    }
    
    for (auto& [x, y] : result) {
        cout << "[" << x << ", " << y << "] ";
    }
    cout << endl;
    return 0;
}
```

**Complexity:** O(n log n + m log m) time.

---

## Q9 — Five Star Sellers (Minimum Operations to Raise Rating)

**Problem:** Given `n` products, each with `(positive_reviews, total_reviews)`. In one operation, add one positive review and one total review to any product. Find minimum operations to get overall percentage of ratings ≥ threshold.

Overall rating = (sum of each product's ratio) / n * 100.

**Constraints:** 1 ≤ n ≤ 10^5

**Approach:** Greedy with max-heap. Always boost the product that gives the largest marginal gain in ratio. The gain of boosting product i is `(a+1)/(b+1) - a/b`.

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, threshold;
    cin >> n >> threshold;
    
    double target = (double)threshold / 100.0 * n;
    double currentSum = 0.0;
    
    // max-heap of {gain, a, b}
    auto gain = [](int a, int b) -> double {
        return (double)(a + 1) / (b + 1) - (double)a / b;
    };
    
    priority_queue<tuple<double, int, int>> pq;
    
    for (int i = 0; i < n; i++) {
        int a, b;
        cin >> a >> b;
        currentSum += (double)a / b;
        pq.push({gain(a, b), a, b});
    }
    
    int ops = 0;
    while (currentSum < target) {
        auto [g, a, b] = pq.top();
        pq.pop();
        currentSum += g;
        ops++;
        pq.push({gain(a + 1, b + 1), a + 1, b + 1});
    }
    
    cout << ops << endl;
    return 0;
}
```

**Complexity:** O(k log n) where k = number of operations needed.

---

## Q10 — Shopping Patterns (Minimum Triangle Weight in Graph)

**Problem:** Given `n` customers and `m` edges (friendships), find a triangle (3 mutual friends) that minimizes the "product score" = sum of degrees of the 3 nodes - 6.

**Constraints:** 1 ≤ n ≤ 3000, 1 ≤ m ≤ 10^5

**Approach:** For each edge (u, v), find common neighbours. For each triangle {u, v, w}, score = deg[u] + deg[v] + deg[w] - 6. Keep minimum.

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    
    vector<int> deg(n + 1, 0);
    vector<unordered_set<int>> adj(n + 1);
    vector<pair<int,int>> edges(m);
    
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].insert(v);
        adj[v].insert(u);
        deg[u]++;
        deg[v]++;
        edges[i] = {u, v};
    }
    
    int ans = INT_MAX;
    
    for (auto& [u, v] : edges) {
        // Find common neighbours
        // Iterate over the smaller adjacency list
        int a = u, b = v;
        if (adj[a].size() > adj[b].size()) swap(a, b);
        
        for (int w : adj[a]) {
            if (w != b && adj[b].count(w)) {
                int score = deg[u] + deg[v] + deg[w] - 6;
                ans = min(ans, score);
            }
        }
    }
    
    cout << (ans == INT_MAX ? -1 : ans) << endl;
    return 0;
}
```

**Complexity:** O(m * sqrt(m)) average case.

---

## Q11 — LRU Cache Misses

**Problem:** Given a cache of size `k` and a sequence of `n` page references, count cache misses using LRU eviction.

**Constraints:** 1 ≤ n ≤ 10^5, 1 ≤ k ≤ n

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, k;
    cin >> n >> k;
    
    list<int> cache;
    unordered_map<int, list<int>::iterator> pos;
    int misses = 0;
    
    for (int i = 0; i < n; i++) {
        int page;
        cin >> page;
        
        if (pos.find(page) != pos.end()) {
            // Hit: move to front
            cache.erase(pos[page]);
        } else {
            // Miss
            misses++;
            if ((int)cache.size() == k) {
                int evict = cache.back();
                cache.pop_back();
                pos.erase(evict);
            }
        }
        cache.push_front(page);
        pos[page] = cache.begin();
    }
    
    cout << misses << endl;
    return 0;
}
```

**Complexity:** O(n) average time, O(k) space.

---

## Q12 — Autoscaling Policy (Utilization Checks)

**Problem:** Given array of CPU utilizations measured every second, starting with `numInstances` instances, apply scaling rules:
- If utilization > 60: double instances (then skip next reading).
- If utilization < 25: halve instances (ceil, then skip next reading).
- Max 2×10^8 instances.

Return final instance count.

**Constraints:** 1 ≤ n ≤ 10^5

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, numInstances;
    cin >> n >> numInstances;
    vector<int> util(n);
    for (int i = 0; i < n; i++) cin >> util[i];
    
    const long long MAX_INST = 200000000LL;
    long long instances = numInstances;
    
    int i = 0;
    while (i < n) {
        if (util[i] > 60) {
            instances = min(instances * 2, MAX_INST);
            i += 2; // skip next
        } else if (util[i] < 25) {
            instances = max(1LL, (instances + 1) / 2);
            i += 2; // skip next
        } else {
            i++;
        }
    }
    
    cout << instances << endl;
    return 0;
}
```

**Complexity:** O(n) time, O(1) space.

---

## Q13 — Music Pairs (Pairs with Total Duration Divisible by 60)

**Problem:** Given array of song durations, count pairs whose total duration is divisible by 60. (LeetCode 1010)

**Constraints:** 1 ≤ n ≤ 5×10^4

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> time(n);
    for (int i = 0; i < n; i++) cin >> time[i];
    
    int count[60] = {};
    long long pairs = 0;
    
    for (int t : time) {
        int rem = t % 60;
        int complement = (60 - rem) % 60;
        pairs += count[complement];
        count[rem]++;
    }
    
    cout << pairs << endl;
    return 0;
}
```

**Complexity:** O(n) time, O(1) space.

---

## Q14 — Move the Obstacle (Shortest Path in Grid with One Removal)

**Problem:** Given n×m grid with 0 (passable) and 1 (obstacle), find shortest path from (0,0) to (n-1,m-1). You can remove at most 1 obstacle. Return shortest path length or -1.

**Constraints:** 1 ≤ n, m ≤ 1000

**Approach:** BFS with state (row, col, obstacle_removed). 

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> grid(n, vector<int>(m));
    for (int i = 0; i < n; i++)
        for (int j = 0; j < m; j++)
            cin >> grid[i][j];
    
    // dist[r][c][k] = min steps to reach (r,c) having removed k obstacles
    vector<vector<array<int,2>>> dist(n, vector<array<int,2>>(m, {INT_MAX, INT_MAX}));
    
    deque<tuple<int,int,int>> bfs; // {row, col, removed}
    dist[0][0][0] = 0;
    bfs.push_back({0, 0, 0});
    
    int dx[] = {0,0,1,-1};
    int dy[] = {1,-1,0,0};
    
    while (!bfs.empty()) {
        auto [r, c, k] = bfs.front();
        bfs.pop_front();
        int d = dist[r][c][k];
        
        if (r == n-1 && c == m-1) {
            cout << d << endl;
            return 0;
        }
        
        for (int i = 0; i < 4; i++) {
            int nr = r + dx[i], nc = c + dy[i];
            if (nr < 0 || nr >= n || nc < 0 || nc >= m) continue;
            
            int nk = k + grid[nr][nc];
            if (nk > 1) continue;
            
            if (d + 1 < dist[nr][nc][nk]) {
                dist[nr][nc][nk] = d + 1;
                bfs.push_back({nr, nc, nk});
            }
        }
    }
    
    cout << -1 << endl;
    return 0;
}
```

**Complexity:** O(n * m) time and space.

---

## Q15 — Subarray Sum Divisible by K (Prefix Sum + Modulo)

**Problem:** Given array of `n` integers and integer `k`, count subarrays whose sum is divisible by `k`. (LeetCode 974)

**Constraints:** 1 ≤ n ≤ 3×10^4

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, k;
    cin >> n >> k;
    vector<int> nums(n);
    for (int i = 0; i < n; i++) cin >> nums[i];
    
    unordered_map<int, int> count;
    count[0] = 1;
    int prefix = 0;
    long long answer = 0;
    
    for (int x : nums) {
        prefix = ((prefix + x) % k + k) % k;
        answer += count[prefix];
        count[prefix]++;
    }
    
    cout << answer << endl;
    return 0;
}
```

**Complexity:** O(n) time, O(k) space.

---

## Q16 — Number of Swaps to Sort (Merge Sort Inversions)

**Problem:** Count the minimum number of adjacent swaps needed to sort an array. This equals the number of inversions.

**Constraints:** 1 ≤ n ≤ 10^5

```cpp
#include <bits/stdc++.h>
using namespace std;

long long mergeCount(vector<int>& arr, int l, int r) {
    if (r - l <= 1) return 0;
    int mid = (l + r) / 2;
    long long cnt = mergeCount(arr, l, mid) + mergeCount(arr, mid, r);
    
    vector<int> tmp;
    int i = l, j = mid;
    while (i < mid && j < r) {
        if (arr[i] <= arr[j]) {
            tmp.push_back(arr[i++]);
        } else {
            tmp.push_back(arr[j++]);
            cnt += mid - i;
        }
    }
    while (i < mid) tmp.push_back(arr[i++]);
    while (j < r) tmp.push_back(arr[j++]);
    copy(tmp.begin(), tmp.end(), arr.begin() + l);
    return cnt;
}

int main() {
    int n;
    cin >> n;
    vector<int> arr(n);
    for (int i = 0; i < n; i++) cin >> arr[i];
    
    cout << mergeCount(arr, 0, n) << endl;
    return 0;
}
```

**Complexity:** O(n log n) time, O(n) space.

---

## Q17 — Minimum Total Container Size (Knapsack Variant)

**Problem:** Given items of various sizes and `d` containers, assign all items to containers sequentially (order preserved). The size of a container is the max item size in it. Minimize total container sizes. (Same as Min Difficulty of Job Schedule — Q7.)

See Q7 solution above — same problem restated.

---

## Q18 — K Closest Points to Origin

**Problem:** Given n points on a plane, find k closest to origin. (LeetCode 973)

**Constraints:** 1 ≤ n ≤ 10^4

```cpp
#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, k;
    cin >> n >> k;
    
    // Max-heap of size k
    priority_queue<pair<long long, int>> pq; // {dist^2, index}
    vector<pair<int,int>> points(n);
    
    for (int i = 0; i < n; i++) {
        cin >> points[i].first >> points[i].second;
        long long d = (long long)points[i].first * points[i].first + 
                      (long long)points[i].second * points[i].second;
        pq.push({d, i});
        if ((int)pq.size() > k) pq.pop();
    }
    
    while (!pq.empty()) {
        int idx = pq.top().second;
        pq.pop();
        cout << points[idx].first << " " << points[idx].second << "\n";
    }
    return 0;
}
```

**Complexity:** O(n log k) time.

---

## Summary of Topics Seen in Recent Amazon OAs (Jan–May 2026)

| Category | Problems |
|----------|----------|
| Heap / Priority Queue | API Throttling, Five Star Sellers, K Closest Points |
| DP | Binary String Sort, Job Schedule, Worker States |
| Binary Search | Use Minimum Tokens |
| Prefix Sum / Hashmap | Find Security Level, Subarray Sum Div K |
| Sliding Window / Two Pointer | Split Prefix Suffix, Music Pairs, Optimal Utilization |
| Graph | Shopping Patterns, Move Obstacle (BFS) |
| Sorting / Greedy | Worker States, Autoscaling |
| Divide & Conquer | Number of Swaps (Inversions) |
| Data Structure Design | LRU Cache |

**New in 2026:** Amazon now includes an AI-assisted code repository round (Spring Boot / Django / MERN) alongside traditional DSA — test debugging and feature completion in a real codebase.
