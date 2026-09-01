import SearchParams, { SearchParamsComponents } from "../../../../core/entity/SearchParams";
import { FmsFileAnnotation } from "../../../../core/services/FileService";

/**
 * Represents an open-source dataset that will be publicly available on the BioFile Finder web version.
 *
 * Currently all types are strings and highly permissive to side-step conversion errors
 */
export interface PublicDatasetProps {
    dataset_id?: string;
    dataset_name: string;
    dataset_path?: string;
    dataset_size?: string;
    description?: string;
    doi?: string;
    featured?: "TRUE" | "FALSE" | "TESTING"; // string indicating dataset category
    file_count?: string;
    group?: string; // Display group name, e.g. "Focal Adhesion" or "Testing"
    index?: string;
    created?: string;
    organization?: string;
    published?: string;
    related_publication?: string;
    related_publication_link?: string;
    specific_query?: string; // A pre-set query that we will attempt to load by default
    version?: string;
    source?: string; // Indicate whether the dataset comes from internal (AICS) or external (other) source
    // Imaging metadata
    cell_line?: string;
    microscopy?: string;
    magnification?: string;
    pixel_size?: string;
    image_width_pixel?: string;
    image_width_um?: string;
    image_height_pixel?: string;
    image_height_um?: string;
    channel_1?: string;
    channel_2?: string;
    channel_3?: string;
    channel_4?: string;
    channel_5?: string;
    channel_6?: string;
    channel_7?: string;
}

export class DatasetAnnotation {
    public displayLabel: string;
    public name: string;
    public minWidth: number;

    constructor(displayLabel: string, name: string, minWidth = 0) {
        this.displayLabel = displayLabel;
        this.name = name;
        this.minWidth = minWidth;
    }

    public equals(target: DatasetAnnotation): boolean {
        return this.displayLabel === target.displayLabel && this.name === target.name;
    }
}

// Originally noted in core/entity/Annotation: TypeScript (3.9) raises an error if this is an enum
// Reference issue without clear resolution: https://github.com/microsoft/TypeScript/issues/6307
/**
 * Matches fields in the dataset manifest to props in this interface
 */
export const DatasetAnnotations = {
    CREATION_DATE: new DatasetAnnotation("Creation date", "created", 112),
    DATASET_ID: new DatasetAnnotation("Dataset ID", "dataset_id"),
    DATASET_NAME: new DatasetAnnotation("Dataset name", "dataset_name", 50),
    DATASET_PATH: new DatasetAnnotation("File Path", "dataset_path"),
    DATASET_SIZE: new DatasetAnnotation("Size", "dataset_size", 78),
    DATASET_DESCRIPTION: new DatasetAnnotation("Short description", "description", 200),
    DOI: new DatasetAnnotation("DOI", "doi"),
    FEATURED: new DatasetAnnotation("Featured", "featured"),
    FILE_COUNT: new DatasetAnnotation("File count", "file_count", 89),
    INDEX: new DatasetAnnotation("Index", "index", 1),
    ORGANIZATION: new DatasetAnnotation("Organization", "organization", 114),
    PUBLICATION_DATE: new DatasetAnnotation("Publication date", "published", 128),
    RELATED_PUBLICATON: new DatasetAnnotation("Related publication", "related_publication", 178),
    RELATED_PUBLICATION_LINK: new DatasetAnnotation(
        "Related publication link",
        "related_publication_link"
    ),
    SOURCE: new DatasetAnnotation("Source", "source"),
    SPECIFIC_QUERY: new DatasetAnnotation("Specific query", "specific_query"),
    VERSION: new DatasetAnnotation("Version", "version"),
    GROUP: new DatasetAnnotation("group", "group"),
    // Imaging metadata
    CELL_LINE: new DatasetAnnotation("Cell line", "cell_line"),
    MICROSCOPY: new DatasetAnnotation("Microscopy", "microscopy"),
    MAGNIFICATION: new DatasetAnnotation("Magnification", "magnification"),
    PIXEL_SIZE: new DatasetAnnotation("Pixel size", "pixel_size"),
    IMAGE_WIDTH_PX: new DatasetAnnotation("Image width (px)", "image_width_pixel"),
    IMAGE_WIDTH_UM: new DatasetAnnotation("Image width (µm)", "image_width_um"),
    IMAGE_HEIGHT_PX: new DatasetAnnotation("Image height (px)", "image_height_pixel"),
    IMAGE_HEIGHT_UM: new DatasetAnnotation("Image height (µm)", "image_height_um"),
    CHANNEL_1: new DatasetAnnotation("Channel 1", "channel_1"),
    CHANNEL_2: new DatasetAnnotation("Channel 2", "channel_2"),
    CHANNEL_3: new DatasetAnnotation("Channel 3", "channel_3"),
    CHANNEL_4: new DatasetAnnotation("Channel 4", "channel_4"),
    CHANNEL_5: new DatasetAnnotation("Channel 5", "channel_5"),
    CHANNEL_6: new DatasetAnnotation("Channel 6", "channel_6"),
    CHANNEL_7: new DatasetAnnotation("Channel 7", "channel_7"),
};

// Limited set used for the details panel
export const DATASET_DISPLAY_FIELDS = [
    DatasetAnnotations.ORGANIZATION,
    DatasetAnnotations.RELATED_PUBLICATON,
    DatasetAnnotations.DOI,
    DatasetAnnotations.PUBLICATION_DATE,
    DatasetAnnotations.CREATION_DATE,
    DatasetAnnotations.FILE_COUNT,
    DatasetAnnotations.DATASET_SIZE,
    // Imaging metadata — rows with empty values are hidden in the details panel
    DatasetAnnotations.CELL_LINE,
    DatasetAnnotations.MICROSCOPY,
    DatasetAnnotations.MAGNIFICATION,
    DatasetAnnotations.PIXEL_SIZE,
    DatasetAnnotations.IMAGE_WIDTH_PX,
    DatasetAnnotations.IMAGE_WIDTH_UM,
    DatasetAnnotations.IMAGE_HEIGHT_PX,
    DatasetAnnotations.IMAGE_HEIGHT_UM,
    DatasetAnnotations.CHANNEL_1,
    DatasetAnnotations.CHANNEL_2,
    DatasetAnnotations.CHANNEL_3,
    DatasetAnnotations.CHANNEL_4,
    DatasetAnnotations.CHANNEL_5,
    DatasetAnnotations.CHANNEL_6,
    DatasetAnnotations.CHANNEL_7,
];

// Limited set used for the table header
export const DATASET_TABLE_FIELDS = [
    DatasetAnnotations.DATASET_NAME,
    DatasetAnnotations.DATASET_DESCRIPTION,
    DatasetAnnotations.CREATION_DATE,
    DatasetAnnotations.RELATED_PUBLICATON,
    DatasetAnnotations.ORGANIZATION,
    DatasetAnnotations.FILE_COUNT,
    DatasetAnnotations.DATASET_SIZE,
];

/**
 * Handles conversion from an FmsFile to a dataset format that can be accepted by IDetailsRow
 */
export default class PublicDataset {
    private datasetDetails: PublicDatasetProps;
    private annotations: FmsFileAnnotation[];

    constructor(datasetDetails: PublicDatasetProps, annotations: FmsFileAnnotation[] = []) {
        this.annotations = annotations;
        if (!annotations?.length) {
            this.datasetDetails = datasetDetails;
        } else {
            const mappedAnnotationsToProps: PublicDatasetProps = {
                dataset_name: datasetDetails.dataset_name,
            };
            Object.values(DatasetAnnotations).forEach((value) => {
                const equivalentAnnotation = annotations.find((e) => e.name === value.displayLabel);
                // csv may set empty fields to string of value 'null'
                if (equivalentAnnotation && equivalentAnnotation.values[0] !== "null") {
                    this.setMetadata(
                        mappedAnnotationsToProps,
                        value.name as keyof PublicDatasetProps,
                        // We currently split on commas, which breaks the description field into multiple values
                        // This is hopefully just a temporary solution, since doesn't work for numbers (e.g., 30,000 becomes 30, 000)
                        equivalentAnnotation.values.join(", ") as string // String casting as temporary measure to avoid type errors
                    );
                }
            });
            this.datasetDetails = mappedAnnotationsToProps;
        }
    }

    public get details(): PublicDatasetProps {
        return this.datasetDetails;
    }

    public get id(): string {
        const id =
            this.datasetDetails.dataset_id ||
            this.getFirstAnnotationValue(DatasetAnnotations.DATASET_ID.displayLabel);
        if (id === undefined) {
            throw new Error("Dataset ID is not defined");
        }
        return id as string;
    }

    public get name(): string {
        return this.datasetDetails.dataset_name;
    }

    public get path(): string {
        const path =
            this.datasetDetails.dataset_path ||
            this.getFirstAnnotationValue(DatasetAnnotations.DATASET_PATH.displayLabel);
        if (path === undefined) {
            throw new Error("Dataset Path is not defined");
        }
        return path as string;
    }

    public get description(): string {
        const description =
            this.datasetDetails.description ||
            this.getFirstAnnotationValue(DatasetAnnotations.DATASET_DESCRIPTION.displayLabel);
        if (description === undefined) {
            return "";
        }
        return description as string;
    }

    public get presetQuery(): SearchParamsComponents | undefined {
        if (!this.datasetDetails.specific_query) {
            return;
        } else {
            return SearchParams.decode(this.datasetDetails.specific_query);
        }
    }

    public get featured(): boolean {
        return this.datasetDetails.featured?.toLowerCase() === "true";
    }

    public get isTest(): boolean {
        return this.datasetDetails.featured?.toLowerCase() === "testing";
    }

    public get group(): string {
        return (this.datasetDetails.group || "").trim();
    }

    public getFirstAnnotationValue(annotationName: string): string | number | boolean | undefined {
        return this.getAnnotation(annotationName)?.values[0];
    }

    public getAnnotation(annotationName: string): FmsFileAnnotation | undefined {
        return this.annotations.find((annotation) => annotation.name === annotationName);
    }

    private setMetadata<K extends keyof PublicDatasetProps, V extends PublicDatasetProps[K]>(
        obj: PublicDatasetProps,
        prop: K,
        value: V
    ) {
        obj[prop] = value;
    }
}
