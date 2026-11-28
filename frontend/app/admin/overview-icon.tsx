import styles from "./overview.module.css";

export function OverviewIcon({ name }: { name: string }) {
  return <span className={styles.icon} aria-hidden="true">{name}</span>;
}
