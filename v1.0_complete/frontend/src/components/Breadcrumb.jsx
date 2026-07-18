import { Link } from "react-router-dom";

/**
 * 面包屑导航
 *
 * @param {Array<{label: string, to?: string}>} items - 面包屑项
 */
export default function Breadcrumb({ items = [] }) {
  return (
    <nav className="breadcrumb">
      {items.map((item, i) => (
        <span key={i}>
          {i > 0 && <span className="sep"> › </span>}
          {item.to ? <Link to={item.to}>{item.label}</Link> : item.label}
        </span>
      ))}
    </nav>
  );
}
