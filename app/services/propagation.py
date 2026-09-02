import networkx as nx


def propagate(G: nx.DiGraph, direct_impacts: dict, decay=0.8, max_depth=3):
    results = dict(direct_impacts)
    frontier = [(node, val, 0) for node, val in direct_impacts.items()]
    while frontier:
        node, shock, depth = frontier.pop(0)
        if depth >= max_depth:
            continue
        for _, downstream, data in G.out_edges(node, data=True):
            transmitted = shock * data["weight"] * decay
            results[downstream] = results.get(downstream, 0) + transmitted
            frontier.append((downstream, transmitted, depth + 1))
    return results


def propagate_with_depth(G: nx.DiGraph, direct_impacts: dict, decay=0.8, max_depth=3):
    """Same traversal as propagate(), but also returns the hop depth each node was first reached at.

    Needed because shock_results.depth records how far a shock propagated, and propagate()
    itself can't change shape without breaking the exact contract it was specified with.
    """
    results = dict(direct_impacts)
    depths = {node: 0 for node in direct_impacts}
    frontier = [(node, val, 0) for node, val in direct_impacts.items()]
    while frontier:
        node, shock, depth = frontier.pop(0)
        if depth >= max_depth:
            continue
        for _, downstream, data in G.out_edges(node, data=True):
            transmitted = shock * data["weight"] * decay
            results[downstream] = results.get(downstream, 0) + transmitted
            if downstream not in depths:
                depths[downstream] = depth + 1
            frontier.append((downstream, transmitted, depth + 1))
    return results, depths
