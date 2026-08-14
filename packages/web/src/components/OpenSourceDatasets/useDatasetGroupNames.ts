import * as React from "react";
import useDatasetDetails from "./useDatasetDetails";

/**
 * Returns an ordered list of unique dataset group names.
 * The "Testing" group is always last; all others appear in their original dataset order.
 */
export default function useDatasetGroupNames(): [string[], boolean] {
    const [allDatasets, isLoading] = useDatasetDetails();

    const groupNames = React.useMemo(() => {
        if (!allDatasets) return [];
        const seen = new Set<string>();
        const order: string[] = [];
        for (const ds of allDatasets) {
            const g = ds.group;
            if (g && !seen.has(g)) {
                seen.add(g);
                order.push(g);
            }
        }
        const nonTest = order.filter((g) => g.toLowerCase() !== "testing");
        const test = order.filter((g) => g.toLowerCase() === "testing");
        return [...nonTest, ...test];
    }, [allDatasets]);

    return [groupNames, isLoading];
}
