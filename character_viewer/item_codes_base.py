from abc import abstractmethod


class ItemCodes:
    @abstractmethod
    def mag_color_codes(self):
        pass

    @abstractmethod
    def element_codes(self):
        pass

    @abstractmethod
    def srank_element_codes(self):
        pass

    @abstractmethod
    def frame_additions(self):
        pass

    @abstractmethod
    def barrier_additions(self):
        pass

    @abstractmethod
    def disk_name_codes(self):
        pass

    @abstractmethod
    def disk_name_language(self):
        pass

    @abstractmethod
    def pb_data_pattern(self):
        pass

    @abstractmethod
    def item_codes(self):
        pass

    def srank_weapon_codes(self):
        return {
            0x007000: "SABER",
            0x007100: "SWORD",
            0x007200: "BLADE",
            0x007300: "PARTISAN",
            0x007400: "SLICER",
            0x007500: "GUN",
            0x007600: "RIFLE",
            0x007700: "MECHGUN",
            0x007800: "SHOT",
            0x007900: "CANE",
            0x007A00: "ROD",
            0x007B00: "WAND",
            0x007C00: "TWIN",
            0x007D00: "CLAW",
            0x007E00: "BAZOOKA",
            0x007F00: "NEEDLE",
            0x008000: "SCYTHE",
            0x008100: "HAMMER",
            0x008200: "MOON",
            0x008300: "PSYCHOGUN",
            0x008400: "PUNCH",
            0x008500: "WINDMILL",
            0x008600: "HARISEN",
            0x008700: "J-BLADE",
            0x008800: "J-CUTTER",
            0x00A500: "SOWRDS",
            0x00A600: "LAUNCHER",
            0x00A700: "CARDS",
            0x00A800: "KNUCKLE",
            0x00A900: "AXE",
        }

    def common_weapon_codes(self):
        return [
            0x000000,
            0x000100,
            0x000101,
            0x000102,
            0x000103,
            0x000104,
            0x000200,
            0x000201,
            0x000202,
            0x000203,
            0x000204,
            0x000300,
            0x000301,
            0x000302,
            0x000303,
            0x000304,
            0x000400,
            0x000401,
            0x000402,
            0x000403,
            0x000404,
            0x000500,
            0x000501,
            0x000502,
            0x000503,
            0x000504,
            0x000600,
            0x000601,
            0x000602,
            0x000603,
            0x000604,
            0x000700,
            0x000701,
            0x000702,
            0x000703,
            0x000704,
            0x000800,
            0x000801,
            0x000802,
            0x000803,
            0x000804,
            0x000900,
            0x000901,
            0x000902,
            0x000903,
            0x000904,
            0x000A00,
            0x000A01,
            0x000A02,
            0x000A03,
            0x000B00,
            0x000B01,
            0x000B02,
            0x000B03,
            0x000C00,
            0x000C01,
            0x000C02,
            0x000C03,
        ]
