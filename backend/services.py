def propagate(G, direct_impacts: dict, decay=0.8, max_depth=3):
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
