# coding=utf-8
# spatial_relations_bbox.py

def _calculate_iou(boxA, boxB):
    # box 格式: [x_min, y_min, x_max, y_max]
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    if interArea == 0:
        return 0.0

    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    iou = interArea / float(boxAArea + boxBArea - interArea)
    return iou

def generate_bbox_relations(scene_graph):
    if not scene_graph or len(scene_graph) < 2:
        return "Not enough objects to determine relative positioning."

    relations = []
    occluded_names = set()
    for i in range(len(scene_graph)):
        for j in range(i + 1, len(scene_graph)):
            a, b = scene_graph[i], scene_graph[j]
            if "bbox_2d" not in a or "bbox_2d" not in b:
                continue
            if _calculate_iou(a["bbox_2d"], b["bbox_2d"]) <= 0.01:
                continue
            z_a = a.get("global_3d_position", {}).get("Z_meters", 999)
            z_b = b.get("global_3d_position", {}).get("Z_meters", 999)
            if z_a < z_b - 0.2:
                occluded_names.add(b.get("name"))
            elif z_b < z_a - 0.2:
                occluded_names.add(a.get("name"))


    # ==============================================================
    # 1. 高度与尺寸链式推导 (Sorted Height Comparison)
    # ==============================================================
    relations.append("=== Size & Height Deductions ===")
    valid_height_objs = [obj for obj in scene_graph if 'Physical_Height' in obj and obj['Physical_Height'] > 0]
    
    if len(valid_height_objs) >= 2:
        # 按物理高度从低到高排序
        sorted_objs = sorted(valid_height_objs, key=lambda x: x['Physical_Height'])
        for i in range(len(sorted_objs) - 1):
            obj_a = sorted_objs[i]
            obj_b = sorted_objs[i+1]
            h_a = obj_a['Physical_Height']
            h_b = obj_b['Physical_Height']
            
            ratio = h_b / h_a
            if obj_a.get("name") in occluded_names or obj_b.get("name") in occluded_names:
                relations.append(
                    "- Size comparison between {} and {} is UNRELIABLE because a bounding box is partially occluded; do not infer actual size from the truncated visible box.".format(
                        obj_a.get("name"), obj_b.get("name")
                    )
                )
            elif ratio > 1.5:
                relations.append(
                    "- {} is CLEARLY SHORTER/SMALLER than {} (estimated height ratio {:.2f}); verify against the image.".format(
                        obj_a.get("name"), obj_b.get("name"), ratio
                    )
                )
            else:
                relations.append(
                    "- {} and {} have APPROXIMATELY SIMILAR HEIGHT within estimation uncertainty.".format(
                        obj_a.get("name"), obj_b.get("name")
                    )
                )
        reliable_heights = [obj["Physical_Height"] for obj in valid_height_objs if obj.get("name") not in occluded_names]
        if occluded_names and len(reliable_heights) >= 2 and max(reliable_heights) / min(reliable_heights) <= 1.5:
            relations.append("- Overall, reliable evidence indicates MOST objects are similar in size; occluded objects do not justify concluding that all objects differ.")
    else:
        # 显式否定兜底
        relations.append("- Not enough valid physical dimensions extracted to compare sizes.")

    # ==============================================================
    # 2. 同一水平线判定 (Horizontal Alignment)
    # ==============================================================
    relations.append("\n=== Horizontal Level Alignment ===")
    valid_base_objs = [obj for obj in scene_graph if 'Bottom_Y_meters' in obj]
    alignment_found = False
    
    for i in range(len(valid_base_objs)):
        for j in range(i + 1, len(valid_base_objs)):
            a, b = valid_base_objs[i], valid_base_objs[j]
            y_diff = abs(a['Bottom_Y_meters'] - b['Bottom_Y_meters'])
            
            # 绝对阈值：底部 Y 坐标相差不到 0.15 米 (15厘米) 认为在同一水平线
            if y_diff <= 0.15:
                relations.append(f"- [Alignment]: The bases of '{a['name']}' and '{b['name']}' are ALIGNED ON THE SAME HORIZONTAL LEVEL.")
                alignment_found = True
                
    if not alignment_found:
        relations.append("- No objects are aligned on the exact same horizontal level.")

    # ==============================================================
    # 3. 遮挡与前后关系推导 (Occlusion & Depth)
    # ==============================================================
    relations.append("\n=== Occlusion & Depth Deductions ===")
    occlusion_found = False
    
    for i in range(len(scene_graph)):
        for j in range(i + 1, len(scene_graph)):
            a, b = scene_graph[i], scene_graph[j]
            if 'bbox_2d' not in a or 'bbox_2d' not in b: continue
            
            iou = _calculate_iou(a['bbox_2d'], b['bbox_2d'])
            if iou > 0.01: # 存在视觉重叠
                z_a = a.get('global_3d_position', {}).get('Z_meters', 999)
                z_b = b.get('global_3d_position', {}).get('Z_meters', 999)
                
                # 深度差大于 0.2 米才确认遮挡，防止贴合太紧的误差
                if z_a < z_b - 0.2:
                    relations.append(f"- [Occlusion]: '{a['name']}' is IN FRONT OF and PARTIALLY OCCLUDES '{b['name']}'.")
                    occlusion_found = True
                elif z_b < z_a - 0.2:
                    relations.append(f"- [Occlusion]: '{b['name']}' is IN FRONT OF and PARTIALLY OCCLUDES '{a['name']}'.")
                    occlusion_found = True

    if not occlusion_found:
        relations.append("- No significant occlusion detected among the extracted objects.")

    return "\n".join(relations)