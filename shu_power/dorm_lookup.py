"""
宿舍查询服务 - 根据中文名称查找房间 ID 链（服务端）
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Optional, List

logger = logging.getLogger(__name__)

# 数据文件路径
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dorm-data.json")


@dataclass
class DormInfo:
    """宿舍完整信息（包含所有 ID）"""
    # 层级名称
    system_name: str
    area_name: str
    district_name: str
    building_name: str
    floor_name: str
    room_name: str
    # 层级 ID (API 所需)
    elcsysid: str
    areaid: str
    districtid: str
    buildid: str
    floorid: str
    roomid: str
    # 完整名称
    full_name: str


class DormLookupService:
    """宿舍查询服务 - 单例缓存数据"""
    
    _instance = None
    _data = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def _load_data(self):
        """加载并缓存 dorm-data.json"""
        if self._data is not None:
            return self._data
        
        if not os.path.exists(DATA_FILE):
            logger.error(f"找不到宿舍数据文件: {DATA_FILE}")
            raise FileNotFoundError(f"Dorm data file not found: {DATA_FILE}")
        
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            self._data = json.load(f)
        
        logger.info(f"✅ 已加载宿舍数据: {len(self._data)} 个系统")
        return self._data
    
    def _get_system_name(self, elcsysid: str) -> str:
        """获取系统名称"""
        system_names = {
            "1": "嘉定校区",
            "2": "宝山校内", 
            "3": "宝山南区",
            "4": "宝山新世纪"
        }
        return system_names.get(elcsysid, f"系统{elcsysid}")
    
    def _normalize_name(self, name: str) -> str:
        """
        标准化名称，统一小写，将中文数字转换为阿拉伯数字，
        并去除 '宝山'、'校区'、'号楼'、'楼'、'房间'、'层' 等冗余成分。
        """
        if not name:
            return ""
        
        name = name.lower().strip()
        
        # 中文数字转换 (1-10)
        num_map = {
            "一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
            "六": "6", "七": "7", "八": "8", "九": "9", "十": "10",
        }
        for cn, ar in num_map.items():
            name = name.replace(cn, ar)
            
        # 去除干扰成分
        # 宝山和校区设为可选，处理 "宝山南区" -> "南区", "嘉定校区" -> "嘉定"
        for part in ["宝山", "校区", "号楼", "楼", "房间", "层"]:
            name = name.replace(part, "")
        
        return name.strip()

    def search(self, keyword: str, limit: int = 10) -> List[DormInfo]:
        """
        根据关键字搜索宿舍
        
        支持的查询格式:
        - "嘉定1号楼 102" -> 匹配 "嘉定一号楼"
        - "嘉定 一号楼 102"
        - "w楼" -> 匹配 "校内W楼"
        """
        data = self._load_data()
        results = []
        
        # 分词并标准化
        raw_tokens = keyword.lower().replace("号楼", "号楼 ").split()
        search_tokens = [self._normalize_name(t) for t in raw_tokens if t.strip()]
        
        if not search_tokens:
            return []
        
        for sys_id, areas in data.items():
            system_name = self._get_system_name(sys_id)
            
            for area in areas:
                area_name = area["name"]
                area_norm = self._normalize_name(area_name)
                areaid = area["id"]
                
                for district in area.get("districts", []):
                    district_name = district["name"]
                    district_norm = self._normalize_name(district_name)
                    districtid = district["id"]
                    
                    for building in district.get("buildings", []):
                        building_name = building["name"]
                        building_norm = self._normalize_name(building_name)
                        buildid = building["id"]
                        
                        for floor in building.get("floors", []):
                            floor_name = floor["name"]
                            floor_norm = self._normalize_name(floor_name)
                            floorid = floor["id"]
                            
                            for room in floor.get("rooms", []):
                                room_name = room["name"]
                                room_norm = self._normalize_name(room_name)
                                roomid = room["id"]
                                
                                # 拼接完整名称用于匹配 (使用标准化后的版本)
                                full_norm = f"{area_norm} {district_norm} {building_norm} {floor_norm} {room_norm}"
                                
                                # 所有搜索 token 都必须在标准化后的全程中出现
                                if all(token in full_norm for token in search_tokens):
                                    results.append(DormInfo(
                                        system_name=system_name,
                                        area_name=area_name,
                                        district_name=district_name,
                                        building_name=building_name,
                                        floor_name=floor_name,
                                        room_name=room_name,
                                        elcsysid=sys_id,
                                        areaid=areaid,
                                        districtid=districtid,
                                        buildid=buildid,
                                        floorid=floorid,
                                        roomid=roomid,
                                        full_name=f"{area_name} {district_name} {building_name} {floor_name} {room_name}".strip(),
                                    ))
                                    
                                    if len(results) >= limit:
                                        return results
        
        return results
    
    def find_exact(self, building: str, room: str) -> Optional[DormInfo]:
        """
        精确查找房间
        
        Args:
            building: 楼栋名称（如 "嘉定1号楼" 或 "嘉定一号楼"）
            room: 房间号（如 "102"）
            
        Returns:
            找到返回 DormInfo，否则返回 None
        """
        # 标准化输入
        building_norm = self._normalize_name(building)
        room_norm = self._normalize_name(room)
        
        # 搜索匹配的房间
        results = self.search(f"{building} {room}", limit=10)
        
        # 精确过滤
        for result in results:
            # 检查楼栋是否匹配 (标准化后)
            res_bld_norm = self._normalize_name(result.building_name)
            res_room_norm = self._normalize_name(result.room_name)
            
            # 如果输入是 "1号楼"，而结果是 "嘉定1号楼"，也算匹配
            if (building_norm in res_bld_norm) and (room_norm == res_room_norm):
                return result
        
        return results[0] if results else None


# 全局服务实例
dorm_service = DormLookupService()
