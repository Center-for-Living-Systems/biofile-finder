import * as React from "react";

import { ModalProps } from "..";
import BaseModal from "../BaseModal";

import styles from "./About.module.css";

/**
 * Dialog meant to show high-level info about BFF
 */
export default function About({ onDismiss }: ModalProps) {
    const body = (
        <div className={styles.container}>
            <p className={styles.text}>
                This BioFile Finder instance is operated by the{" "}
                <a
                    href="https://gardel.uchicago.edu"
                    className={styles.link}
                    target="_blank"
                    rel="noreferrer"
                >
                    Center for Living Systems
                </a>{" "}
                at the University of Chicago. It is built on the open-source{" "}
                <a
                    href="https://github.com/AllenInstitute/biofile-finder"
                    className={styles.link}
                    target="_blank"
                    rel="noreferrer"
                >
                    BioFile Finder
                </a>{" "}
                developed by the Allen Institute for Cell Science, designed to streamline how you
                search, access, and visualize imaging datasets.
            </p>
            <h3>Contact</h3>
            <ul className={styles.contactList}>
                <li>
                    Questions or feedback: contact{" "}
                    <a href="mailto:liyading@uchicago.edu" className={styles.link}>
                        Liya Ding (liyading@uchicago.edu)
                    </a>
                    .
                </li>
                <li>
                    Upstream source code:{" "}
                    <a
                        href="https://github.com/AllenInstitute/biofile-finder"
                        className={styles.link}
                        target="_blank"
                        rel="noreferrer"
                    >
                        github.com/AllenInstitute/biofile-finder
                    </a>
                    .
                </li>
            </ul>
        </div>
    );

    return <BaseModal body={body} onDismiss={onDismiss} title="About" />;
}
