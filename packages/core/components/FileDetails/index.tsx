import { DefaultButton, Modal } from "@fluentui/react"; // DefaultButton kept for "View relationship diagram"
import classNames from "classnames";
import * as React from "react";
import { useDispatch, useSelector } from "react-redux";

import FileAnnotationList from "./FileAnnotationList";
import InlineImageViewer from "./InlineImageViewer";
import Pagination from "./Pagination";
import useThumbnailPath from "./useThumbnailPath";
import { TertiaryButton, TransparentIconButton } from "../Buttons";
import Tooltip from "../Tooltip";
import { ROOT_ELEMENT_ID } from "../../App";
import FileThumbnail from "../../components/FileThumbnail";
import FileDetail from "../../entity/FileDetail";
import useDownloadFiles from "../../hooks/useDownloadFiles";
import useTruncatedString from "../../hooks/useTruncatedString";
import { selection } from "../../state";

import styles from "./FileDetails.module.css";

interface Props {
    className?: string;
    fileDetails: FileDetail | undefined;
    isLoading?: boolean;
    onClose?: () => void;
}

const FILE_DETAILS_PANE_ID = "file-details-pane";
const FILE_DETAILS_WIDTH_ATTRIBUTE = "--file-details-width";

function resizeHandleOnMouseDown(mouseDownEvent: React.MouseEvent<HTMLDivElement>) {
    const rootElement: HTMLElement | null = document.getElementById(ROOT_ELEMENT_ID);
    const fileDetailsPane: HTMLElement | null = document.getElementById(FILE_DETAILS_PANE_ID);
    // This _should_ always be true, but is otherwise not a huge deal
    if (rootElement && fileDetailsPane) {
        fileDetailsPane.classList.remove(styles.expandableTransition);

        const startingWidth = fileDetailsPane.offsetWidth;
        const startingPageX = mouseDownEvent.pageX;

        const resizeHandleRootOnMouseMove = (mouseMoveEvent: MouseEvent) => {
            mouseMoveEvent.preventDefault();
            const newWidth = startingWidth + (startingPageX - mouseMoveEvent.pageX);

            if (mouseMoveEvent.buttons === 1 && newWidth >= 175) {
                // If primary button (left-click) is still pressed and newWidth is still greater
                // than the minimum width we want for the pane
                rootElement.style.setProperty(FILE_DETAILS_WIDTH_ATTRIBUTE, `${newWidth}px`);
            } else {
                // Remove this listener if user releases the primary button
                rootElement.removeEventListener("mousemove", resizeHandleRootOnMouseMove);
                fileDetailsPane.classList.add(styles.expandableTransition);
            }
        };

        rootElement.addEventListener("mousemove", resizeHandleRootOnMouseMove);
    } else {
        console.log(`"${ROOT_ELEMENT_ID}" element or "${FILE_DETAILS_PANE_ID}" element not found`);
    }
}

function resizeHandleDoubleClick() {
    const rootElement: HTMLElement | null = document.getElementById(ROOT_ELEMENT_ID);
    const fileDetailsPane: HTMLElement | null = document.getElementById(FILE_DETAILS_PANE_ID);

    if (rootElement && fileDetailsPane) {
        // Return details pane width to the default (20%)
        fileDetailsPane.classList.add(styles.expandableTransition);
        rootElement.style.setProperty(FILE_DETAILS_WIDTH_ATTRIBUTE, "20%");
    } else {
        console.log(`"${ROOT_ELEMENT_ID}" element or "${FILE_DETAILS_PANE_ID}" element not found`);
    }
}

/**
 * Displays details of selected file(s).
 */
export default function FileDetails(props: Props) {
    const dispatch = useDispatch();
    const hasProvenanceSource = useSelector(selection.selectors.hasProvenanceSource);

    const truncatedFileName = useTruncatedString(props.fileDetails?.name || "", 30);
    const { isThumbnailLoading, thumbnailPath } = useThumbnailPath(props.fileDetails);
    const { isDownloadDisabled, disabledDownloadReason, onDownload } = useDownloadFiles(
        props.fileDetails
    );
    const [isFullscreenThumbnail, setIsFullscreenThumbnail] = React.useState(false);
    const isThumbnailClickable = !!thumbnailPath && !isThumbnailLoading;
    const previewUrl = props.fileDetails?.annotations.find(
        (a) => typeof a.values[0] === "string" && String(a.values[0]).includes("viewer.html?meta=")
    )?.values[0] as string | undefined;
    // Debug: log annotation names and the found previewUrl
    if (props.fileDetails) {
        console.log(
            "[Preview debug] annotations:",
            props.fileDetails.annotations.map((a) => `${a.name}=${a.values[0]}`)
        );
        console.log("[Preview debug] previewUrl:", previewUrl);
    }
    const [previewOpen, setPreviewOpen] = React.useState(false);
    // Close preview panel when a different file is selected
    React.useEffect(() => {
        setPreviewOpen(false);
    }, [props.fileDetails?.uid]);

    return (
        <div
            className={classNames(styles.root, styles.expandableTransition, props.className)}
            id={FILE_DETAILS_PANE_ID}
        >
            <div
                className={styles.resizeHandle}
                onMouseDown={(e) => resizeHandleOnMouseDown(e)}
                onDoubleClick={resizeHandleDoubleClick}
            >
                <div />
            </div>
            <div className={styles.paginationAndContent}>
                <div className={styles.overflowContainer}>
                    {props.fileDetails && (
                        <>
                            <div className={styles.header}>
                                <div className={styles.leftAlign}>
                                    <Pagination className={styles.pagination} />
                                </div>
                                {/* spacing component */}
                                <div className={styles.gutter}></div>
                                <div className={styles.rightAlign}>
                                    <Tooltip content={disabledDownloadReason}>
                                        <TertiaryButton
                                            className={styles.tertiaryButton}
                                            disabled={isDownloadDisabled}
                                            iconName="Download"
                                            id="download-file-button"
                                            title={`Download file ${truncatedFileName} to local system`}
                                            onClick={onDownload}
                                        />
                                    </Tooltip>
                                    {props.onClose && (
                                        <TransparentIconButton
                                            className={styles.clearButton}
                                            iconName="Clear"
                                            onClick={props.onClose}
                                        />
                                    )}
                                </div>
                            </div>
                            <p className={styles.fileName}>{props.fileDetails?.name}</p>
                            <div
                                className={classNames(styles.thumbnailContainer, {
                                    [styles.thumbnailContainerClickable]: isThumbnailClickable,
                                })}
                                onClick={() =>
                                    isThumbnailClickable && setIsFullscreenThumbnail(true)
                                }
                                onKeyDown={(e) => {
                                    if (
                                        (e.key === "Enter" || e.key === " ") &&
                                        isThumbnailClickable
                                    ) {
                                        e.preventDefault();
                                        setIsFullscreenThumbnail(true);
                                    }
                                }}
                                role={isThumbnailClickable ? "button" : undefined}
                                tabIndex={isThumbnailClickable ? 0 : undefined}
                                title={isThumbnailClickable ? "Click to enlarge" : undefined}
                            >
                                <FileThumbnail
                                    className={styles.thumbnail}
                                    width="100%"
                                    uri={thumbnailPath}
                                    loading={isThumbnailLoading}
                                />
                            </div>
                            <Modal
                                isOpen={isFullscreenThumbnail}
                                onDismiss={() => setIsFullscreenThumbnail(false)}
                                containerClassName={styles.fullscreenModalContainer}
                                overlay={{ className: styles.fullscreenOverlay }}
                                isBlocking={false}
                            >
                                <img
                                    alt={props.fileDetails?.name}
                                    className={styles.fullscreenImage}
                                    src={thumbnailPath}
                                    tabIndex={0}
                                    onClick={() => setIsFullscreenThumbnail(false)}
                                    onKeyDown={(e) => {
                                        if (e.key === "Enter" || e.key === " ") {
                                            e.preventDefault();
                                            setIsFullscreenThumbnail(false);
                                        }
                                    }}
                                />
                            </Modal>
                            <div className={styles.titleRow}>
                                <h4>Metadata</h4>
                                {hasProvenanceSource && (
                                    <DefaultButton
                                        onClick={() =>
                                            dispatch(
                                                selection.actions.changeProvenanceOriginId(
                                                    props.fileDetails?.uid
                                                )
                                            )
                                        }
                                    >
                                        View relationship diagram
                                    </DefaultButton>
                                )}
                            </div>
                            <FileAnnotationList
                                className={styles.annotationList}
                                fileDetails={props.fileDetails}
                                isLoading={!!props.isLoading}
                                onPreviewClick={
                                    previewUrl ? () => setPreviewOpen((o) => !o) : undefined
                                }
                            />
                        </>
                    )}
                </div>
            </div>
            {previewOpen && previewUrl && (
                <div
                    style={{
                        position: "fixed",
                        bottom: 0,
                        left: 0,
                        right: 0,
                        height: "65vh",
                        background: "#1a1a1a",
                        borderTop: "2px solid #333",
                        zIndex: 1000,
                        display: "flex",
                        flexDirection: "column",
                        overflow: "hidden",
                    }}
                >
                    <div
                        style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            padding: "6px 12px",
                            borderBottom: "1px solid #2a2a2a",
                            flexShrink: 0,
                        }}
                    >
                        <span style={{ fontSize: 12, color: "#888" }}>
                            {props.fileDetails?.name}
                        </span>
                        <button
                            onClick={() => setPreviewOpen(false)}
                            style={{
                                background: "none",
                                border: "none",
                                color: "#888",
                                cursor: "pointer",
                                fontSize: 16,
                                lineHeight: 1,
                                padding: "0 4px",
                            }}
                            title="Close preview"
                        >
                            ✕
                        </button>
                    </div>
                    <div
                        style={{
                            flex: 1,
                            overflow: "hidden",
                            padding: "8px 12px",
                            display: "flex",
                            flexDirection: "column",
                            minHeight: 0,
                        }}
                    >
                        <InlineImageViewer previewUrl={previewUrl} />
                    </div>
                </div>
            )}
        </div>
    );
}
