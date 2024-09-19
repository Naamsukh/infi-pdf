
# Function to calculate the overlapping area
def calculate_overlap_area(r1, r2):
    x1, y1, w1, h1 = r1
    x2, y2, w2, h2 = r2

    overlap_x = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
    overlap_y = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))

    return overlap_x, overlap_y

def extract_coordinates_from_object(obj):
    points = obj["metadata"]["coordinates"]["points"]
    
    x1, y1 = points[0]
    x2, y2 = points[2]
    
    w = x2 - x1
    h = y2 - y1
    
    return x1, y1, w, h


# Function to adjust overlapping objects
def adjust_overlapping_objects_in_ppt(objects):
    adjusted_objects= objects.copy()

    for i, obj1  in enumerate(adjusted_objects):
        for j, obj2 in enumerate(adjusted_objects):
            if i != j:

                r1 = extract_coordinates_from_object(obj1)
                r2 = extract_coordinates_from_object(obj2)

                # Calculate overlap area
                overlap_w, overlap_h = calculate_overlap_area(r1, r2)

                if overlap_w > 0 and overlap_h > 0:
                    # Adjust sizes to divide overlap equally
                    x1, y1, w1, h1 = r1
                    x2, y2, w2, h2 = r2

                    # Adjust the width and height of the rectangles
                    new_w1 = w1 - overlap_w / 2
                    new_w2 = w2 - overlap_w / 2
                    new_h1 = h1 - overlap_h / 2
                    new_h2 = h2 - overlap_h / 2

                    # Update the rectangles with new positions and sizes
                    adjusted_objects[i]["metadata"]["coordinates"]["points"] = [
                        [x1, y1], [x1, y1 + new_h1], [x1 + new_w1, y1 + new_h1], [x1 + new_w1, y1]
                    ]
                    adjusted_objects[j]["metadata"]["coordinates"]["points"] = [
                        [x2 + overlap_w / 2, y2 + overlap_h / 2],
                        [x2 + overlap_w / 2, y2 + new_h2 + overlap_h / 2],
                        [x2 + new_w2 + overlap_w / 2, y2 + new_h2 + overlap_h / 2],
                        [x2 + new_w2 + overlap_w / 2, y2 + overlap_h / 2]
                    ]
    return adjusted_objects

def check_overlap(rect1, rect2):
    # Extract the top-left and bottom-right coordinates of each rectangle
    x1_min, y1_min = rect1[0]
    x1_max, y1_max = rect1[2]

    x2_min, y2_min = rect2[0]
    x2_max, y2_max = rect2[2]

    # Check if rectangles overlap
    return not (x1_max < x2_min or x2_max < x1_min or y1_max < y2_min or y2_max < y1_min)

def find_unique_overlapping_and_non_overlapping_objects(data):
    overlapping_objects = set()
    all_objects = {}
    
    # Iterate over each pair of objects
    for i in range(len(data)):
      obj1 = data[i]
      rect1 = obj1['metadata']['coordinates']['points']
      all_objects[obj1['element_id']] = obj1
      
      for j in range(i + 1, len(data)):
        obj2 = data[j]
        rect2 = obj2['metadata']['coordinates']['points']
        all_objects[obj2['element_id']] = obj2
        
        # Check if the two objects overlap
        if check_overlap(rect1, rect2):
          overlapping_objects.add(obj1['element_id'])
          overlapping_objects.add(obj2['element_id'])
    
    # Create lists of overlapping and non-overlapping objects
    overlapping_list = [all_objects[id] for id in overlapping_objects]
    non_overlapping_list = [obj for id, obj in all_objects.items() if id not in overlapping_objects]
    
    return overlapping_list, non_overlapping_list