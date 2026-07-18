import { useState } from "react";

/**
 * 知识点卡片
 * 展示：
 * - 标题
 * - 描述
 * - 分类
 * - 重要程度
 * - 时间定位
 * - 展开详情
 */

const IMPORTANCE_STARS = {
  1: "★☆☆☆☆",
  2: "★★☆☆☆",
  3: "★★★☆☆",
  4: "★★★★☆",
  5: "★★★★★",
};

const CATEGORY_COLORS = {
  "基础概念": "#007aff",
  "算法原理": "#ff9500",
  "工具使用": "#34c759",
  "实践技巧": "#ff3b30",
  "行业应用": "#667eea",
};

function formatTime(seconds) {
  if (seconds === null || seconds === undefined) {
    return null;
  }

  const min = Math.floor(seconds / 60);
  const sec = Math.floor(seconds % 60);

  return `${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}


export default function KnowledgePointCard({ point, onSeek }) {

  const [expanded, setExpanded] = useState(false);

  const catColor =
    CATEGORY_COLORS[point.category] || "#999";

  const stars =
    IMPORTANCE_STARS[point.importance] || "";


  return (
    <div
      className="card"
      style={{
        marginBottom: 12,
        borderLeft:`3px solid ${catColor}`,
        cursor:"pointer",
      }}
      onClick={() => setExpanded(!expanded)}
    >

      {/* 顶部 */}
      <div
        style={{
          display:"flex",
          justifyContent:"space-between",
          alignItems:"center",
          marginBottom:8,
        }}
      >

        <h4
          style={{
            fontSize:"1rem",
            margin:0,
          }}
        >
          {point.title}
        </h4>


        <div
          style={{
            display:"flex",
            alignItems:"center",
            gap:8,
          }}
        >

          <span
            style={{
              color:"#f5a623",
              fontSize:"0.8rem",
            }}
          >
            {stars}
          </span>


          {point.category && (
            <span
              style={{
                fontSize:"0.7rem",
                padding:"2px 8px",
                borderRadius:5,
                color:catColor,
                background:`${catColor}15`,
              }}
            >
              {point.category}
            </span>
          )}

        </div>

      </div>


      {/* 简介 */}
      {
        point.description &&
        <p
          style={{
            margin:"6px 0",
            color:"#666",
            lineHeight:1.6,
            fontSize:"0.9rem",
          }}
        >
          {point.description}
        </p>
      }



      {/* 展开提示 */}
      <div
        style={{
          marginTop:8,
          fontSize:"0.75rem",
          color:"#999",
          textAlign:"right",
        }}
      >
        {
          expanded
          ? "收起 ▲"
          : "查看详情 ▼"
        }
      </div>



      {/* 详情 */}
      {
        expanded &&
        <div
          style={{
            marginTop:12,
            paddingTop:12,
            borderTop:"1px solid #eee",
            fontSize:"0.85rem",
            color:"#555",
          }}
        >

          {
            point.timestamp !== null &&
            point.timestamp !== undefined &&
            (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onSeek && onSeek(point.timestamp);
                }}
                style={{
                  marginBottom: 6,
                  border: "none",
                  background: "transparent",
                  padding: 0,
                  color: "#007aff",
                  cursor: "pointer",
                  fontSize: "0.85rem",
                }}
              >
                🔊 音频位置：
                <b>
                  {formatTime(point.timestamp)}
                </b>
              </button>
            )
          }

          <div>
            ⭐ 重要程度：

            <span
              style={{
                color:"#f5a623",
                marginLeft:5,
              }}
            >
              {stars}
            </span>

          </div>


        </div>
      }

    </div>
  );
}