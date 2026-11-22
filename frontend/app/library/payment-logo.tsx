import Image from "next/image";
import styles from "./payment-methods.module.css";

export default function PaymentLogo({ provider }: { provider: "pix" | "mercadopago" }) {
  return <span className={styles.logo} aria-hidden="true">
    <Image src={`/payments/${provider}.svg`} alt="" width={40} height={40} unoptimized />
  </span>;
}
