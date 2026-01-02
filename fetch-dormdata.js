//该脚本内容需要在浏览器console执行 确保token有效

(async function () {
    const rawToken = ""; // 填入你的 token
    const token = "Bearer " + rawToken;
    const baseUrl = "/openservice/miniprogram";
    const headers = { "Content-Type": "application/json", "sw-authorization": token };
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));

    async function fetchList(endpoint, payload) {
        try {
            await sleep(150);
            const res = await fetch(`${baseUrl}/${endpoint}`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(payload)
            });
            const json = await res.json();

            // 自动拆解两层包装
            let list = (json.data && json.data.data) ? json.data.data : (json.data || []);
            if (!Array.isArray(list)) return [];

            // 字段名弹性映射
            return list.map(item => {
                const idKey = Object.keys(item).find(k => k.toLowerCase().endsWith('id'));
                const nameKey = Object.keys(item).find(k => k.toLowerCase().includes('name'));
                return {
                    id: item[idKey] || item.id,
                    name: item[nameKey] || item.name,
                    raw: item
                };
            });
        } catch (e) {
            return [];
        }
    }

    const systems = [
        { id: "1", name: "嘉定校区" },
        { id: "2", name: "宝山校内" },
        { id: "3", name: "宝山南区" },
        { id: "4", name: "宝山新世纪" }
    ];

    console.log("🚀 开始构建全校电控 ID 科学地图...");
    const masterMap = {};

    for (const sys of systems) {
        console.log(`\n📦 正在扫描系统: ${sys.name}`);
        const areas = await fetchList("queryarea", { elcsysid: sys.id });

        for (const area of areas) {
            console.log(`  └── 校区: ${area.name} (ID: ${area.id})`);
            const districts = await fetchList("querydistricts", { elcsysid: sys.id, areaid: area.id });

            for (const dist of districts) {
                console.log(`      └── 区域: ${dist.name} (ID: ${dist.id})`);
                const builds = await fetchList("querybuilds", { elcsysid: sys.id, areaid: area.id, districtid: dist.id });

                for (const bld of builds) {
                    const floors = await fetchList("queryfloors", {
                        elcsysid: sys.id, areaid: area.id, districtid: dist.id, buildid: bld.id
                    });

                    if (floors.length > 0) {
                        console.log(`          🏢 ${bld.name} (ID: ${bld.id}) -> 发现 ${floors.length} 层`);
                    }

                    for (const flr of floors) {
                        const rooms = await fetchList("queryrooms", {
                            elcsysid: sys.id, areaid: area.id, districtid: dist.id, buildid: bld.id, floorid: flr.id
                        });
                        flr.rooms = rooms;
                    }
                    bld.floors = floors;
                }
                dist.buildings = builds;
            }
            area.districts = districts;
        }
        masterMap[sys.id] = areas;
    }

    console.log("✅ 全部数据映射完成！");
    window.SHU_DORM_RESULT = masterMap; // 存入全局变量
    console.log("📋 数据已存入 window.SHU_DORM_RESULT。");
})();