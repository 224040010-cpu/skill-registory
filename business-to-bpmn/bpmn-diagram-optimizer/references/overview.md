# BPMN Diagram Optimizer · 能力概述

对 BPMN 工作流进行单次综合优化：布局（正交布线、合理间距）、视觉美化（按元素类型着色）、标签重叠解决。合并原 layouting、styling、label-resolving 三步为一次处理。

**输入**：bpmn_xml。**输出**：optimized_xml、layout_stats。详见 `api-reference.md`。

仅修改 BPMNDI 层面的坐标与视觉属性，不修改流程逻辑。输出可在 bpmn.io 中直接打开并呈现优化后的图表。
