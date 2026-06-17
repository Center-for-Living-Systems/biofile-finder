import * as React from "react";

import styles from "./Footer.module.css";

export default function Footer() {
    // OneTrust cookie-settings button removed: the OneTrust SDK is an Allen-only
    // integration not loaded in this self-hosted build, so the button was dead.
    return <div className={styles.footer} />;
}
