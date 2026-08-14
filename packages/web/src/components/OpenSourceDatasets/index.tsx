import * as React from "react";
import { useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";

import DatasetTable from "./DatasetTable";
import DatasetDetails from "../DatasetDetails";
import PublicDataset from "../../entity/PublicDataset";
import Modal from "../../../../core/components/Modal";
import { metadata, selection } from "../../../../core/state";
import SearchParams, {
    SearchParamsComponents,
    getNameAndTypeFromSourceUrl,
    Source,
} from "../../../../core/entity/SearchParams";

import styles from "./OpenSourceDatasets.module.css";
/**
 * Page for displaying public-facing datasets
 * Currently using placeholder text and data
 */
export default function OpenSourceDatasets() {
    const dispatch = useDispatch();
    const navigate = useNavigate();

    // Begin request action so dataset manifest is ready for table child component
    React.useEffect(() => {
        dispatch(metadata.actions.requestDatasetManifest("Dataset Manifest"));
    }, [dispatch]);

    const openDatasetInApp = (
        datasetName: string,
        source: Source,
        url?: Partial<SearchParamsComponents>
    ) => {
        dispatch(
            selection.actions.addQuery({
                name: `New ${source.name} Query on ${datasetName || "open-source dataset"}`,
                parts: { ...url, sources: [source] },
            })
        );

        // The initialization function automatically parses and adds queries from the
        // url search params
        navigate({
            pathname: "/app",
            search: `?${SearchParams.encode({
                ...url,
                sources: [source],
            })}`,
        });
    };

    const loadDataset = (datasetDetails?: PublicDataset) => {
        if (!datasetDetails) throw new Error("No dataset provided");

        const dataSourceURL = datasetDetails.path;
        const url = datasetDetails?.presetQuery;
        openDatasetInApp(
            datasetDetails.name,
            {
                ...getNameAndTypeFromSourceUrl(dataSourceURL),
                uri: dataSourceURL,
            },
            url
        );
    };

    return (
        <>
            <div className={styles.scroll}>
                <div className={styles.banner}>
                    <div className={styles.bannerContent}>
                        <div className={styles.bannerContentText}>
                            <div className={styles.bannerHeader}> Open-source datasets</div>
                            <div className={styles.bannerBody}>
                                The datasets below are available for exploration and open use. Click
                                LOAD to open a dataset in BioFile Finder, view images in your web
                                browser, download files, or share selected subdatasets as links.
                            </div>
                        </div>
                    </div>
                </div>
                <div className={styles.content}>
                    <h2 className={styles.tableTitle}>Sub-cellular Structure Datasets</h2>
                    <p>
                        Confocal fluorescence datasets from the Gardel Lab, featuring multi-channel
                        focal adhesion markers imaged in living cells.
                    </p>
                    <DatasetTable onLoadDataset={loadDataset} category="featured" />
                    <h2 className={styles.tableTitle}>Testing datasets</h2>
                    <p>
                        Experimental datasets used during BioFile Finder development. Not intended
                        for production use.
                    </p>
                    <DatasetTable onLoadDataset={loadDataset} category="testing" />
                    <p>
                        Want to include your dataset? Send us a request at
                        <a
                            className={styles.link}
                            href="mailto:aics_software_support@alleninstitute.org"
                        >
                            &nbsp;aics_software_support@alleninstitute.org&nbsp;
                        </a>
                        and we can discuss including your data. Please note that your image data
                        would need to be stored in a public location like
                        <a
                            className={styles.link}
                            href="https://idr.openmicroscopy.org/"
                            target="_blank"
                            rel="noreferrer"
                        >
                            &nbsp;the Image Data Resource&nbsp;
                        </a>{" "}
                        or AWS.
                    </p>
                </div>
            </div>
            <DatasetDetails onLoadDataset={loadDataset} />
            <Modal />
        </>
    );
}
