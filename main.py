import heapq, re
from collections import defaultdict, Counter
import typing

from fastapi import FastAPI, Query

WORD_RE = re.compile(r'\b[a-zA-Z0-9]+\b')

class TrieNode:
    def __init__(self):
        self.children: dict[str, TrieNode] = {}
        self.end = False
class Trie:
    def __init__(self): self.root = TrieNode()
    def insert(self, word: str) -> None:
        n=self.root
        for c in word.lower(): n=n.children.setdefault(c,TrieNode())
        n.end=True
    def suggest(self, prefix: str, limit: int = 8) -> list[str]:
        if limit <= 0: return []
        n=self.root
        for c in prefix.lower():
            if c not in n.children: return []
            n=n.children[c]
        out: list[str] = []
        def walk(node: TrieNode, s: str) -> None:
            if len(out)>=limit:return
            if node.end:out.append(s)
            for c,ch in sorted(node.children.items()):walk(ch,s+c)
        walk(n,prefix.lower()); return out

class SearchEngine:
    def __init__(self):
        self.docs: dict[int, dict[str, typing.Any]] = {}
        self.index: defaultdict[str, set[int]] = defaultdict(set)
        self.trie = Trie()
        self.graph: defaultdict[int, set[typing.Any]] = defaultdict(set)
    def add(self, title: str, text: str, links: typing.Iterable[typing.Any] | None = None) -> None:
        i=len(self.docs); document_links=list(links or [])
        self.docs[i]={'title':title,'text':text,'links':document_links}
        words=WORD_RE.findall((title+' '+text).lower()); counts=Counter(words)
        self.docs[i]['counts']=counts
        for w in counts: self.index[w].add(i); self.trie.insert(w)
        self.graph[i].update(document_links)
    def search(self, q: str, limit: int = 10) -> list[tuple[dict[str, typing.Any], float]]:
        if limit <= 0: return []
        terms=WORD_RE.findall(q.lower()); scores: defaultdict[int, float] = defaultdict(float)
        N=max(len(self.docs),1)
        for term in terms:
            for i in self.index.get(term,[]):
                tf=self.docs[i]['counts'][term]; df=len(self.index[term])
                idf=1+(N/(1+df)); scores[i]+=tf*idf
        # small title and link boosts
        for i in list(scores):
            title_terms=set(WORD_RE.findall(self.docs[i]['title'].lower()))
            scores[i]+=sum(2 for t in terms if t in title_terms)
            scores[i]+=0.15*len(self.graph[i])
        best: list[tuple[int, float]] = heapq.nlargest(limit, scores.items(), key=lambda item: item[1])
        return [(self.docs[i],round(s,2)) for i,s in best]

def demo():
    e=SearchEngine()
    e.add('Python Programming','Python is a popular programming language used for web development, data science and automation.')
    e.add('Data Structures','Data structures include arrays, linked lists, stacks, queues, trees, heaps, graphs and hash maps.')
    e.add('Machine Learning','Machine learning uses algorithms and data to build predictive models. Python is widely used in ML.')
    e.add('Graph Algorithms','Graph algorithms include BFS, DFS, Dijkstra shortest path and PageRank.')
    e.add('Web Development','FastAPI and React can be used to build modern web applications with Python and JavaScript.')
    return e


app = FastAPI(title='Mini Search Engine')
engine = demo()


@app.get('/')
def home() -> dict[str, str]:
    return {'message': 'Mini Search Engine API', 'docs': '/docs'}


@app.get('/search')
def search(q: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=50)) -> list[dict[str, typing.Any]]:
    results = engine.search(q, limit)
    return [
        {
            'title': document['title'],
            'text': document['text'],
            'links': document['links'],
            'score': score,
        }
        for document, score in results
    ]


@app.get('/suggest')
def suggest(prefix: str = '', limit: int = Query(8, ge=1, le=50)) -> list[str]:
    return engine.trie.suggest(prefix, limit)

if __name__=='__main__':
    e=demo(); print('Suggestions:',e.trie.suggest('py'))
    for d,s in e.search('python machine learning'): print(f'{s:>6}  {d["title"]}')
