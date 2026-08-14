import * as React from "react";
import { useRouteError } from "react-router";

import styles from "./ErrorPage.module.css";

/**
 * Error page for displaying an uncaught failure in the application
 */
export default function ErrorPage() {
    const error = useRouteError() as Error | undefined;

    return (
        <div className={styles.container}>
            <h1>Uh oh!</h1>
            <p>
                An unexpected error has bubbled up, we are not sure exactly what went wrong, but
                below is the error we caught.
                <br />
                For help, contact{" "}
                <a href="mailto:liyading@uchicago.edu">Liya Ding (liyading@uchicago.edu)</a>.
            </p>
            <div className={styles.error}>
                <h3>Error</h3>
                <p>{error?.message || "Unknown error"}</p>
            </div>
        </div>
    );
}
