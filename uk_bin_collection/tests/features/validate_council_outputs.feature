Feature: Test each council output matches expected results

    Scenario Outline: Validate Council Output
        Given the council: <council>
        When we scrape the data from <council> using <selenium_mode> and the <selenium_url> is set
        Then the result is valid json
        And the output should validate against the schema

		@AdurAndWorthingCouncils
		Examples: AdurAndWorthingCouncils
		| council | selenium_url | selenium_mode |
		| AdurAndWorthingCouncils | None  | None  |

		@ArunCouncil
		Examples: ArunCouncil
		| council | selenium_url | selenium_mode |
		| ArunCouncil | http://selenium:4444/wd/hub:4444  | remote  |

        @AylesburyValeCouncil
		Examples: AylesburyValeCouncil
		| council | selenium_url | selenium_mode |
		| AylesburyValeCouncil | None  | None  |

        @BarnetCouncil
		Examples: BarnetCouncil
		| council | selenium_url | selenium_mode |
		| BarnetCouncil | http://selenium:4444  | local  |

        @BarnsleyMBCouncil
		Examples: BarnsleyMBCouncil
		| council | selenium_url | selenium_mode |
		| BarnsleyMBCouncil | None  | None  |

        @BasingstokeCouncil
		Examples: BasingstokeCouncil
		| council | selenium_url | selenium_mode |
		| BasingstokeCouncil | None  | None  |

        @BathAndNorthEastSomersetCouncil
		Examples: BathAndNorthEastSomersetCouncil
		| council | selenium_url | selenium_mode |
		| BathAndNorthEastSomersetCouncil | None  | None  |

        @BCPCouncil
		Examples: BCPCouncil
		| council | selenium_url | selenium_mode |
		| BCPCouncil | None  | None  |

		@BedfordBoroughCouncil
		Examples: BedfordBoroughCouncil
		| council | selenium_url | selenium_mode |
		| BedfordBoroughCouncil | None  | None  |

        @BedfordshireCouncil
		Examples: BedfordshireCouncil
		| council | selenium_url | selenium_mode |
		| BedfordshireCouncil | None  | None  |

        @BexleyCouncil
		Examples: BexleyCouncil
		| council | selenium_url | selenium_mode |
		| BexleyCouncil | http://selenium:4444  | local  |

        @BirminghamCityCouncil
		Examples: BirminghamCityCouncil
		| council | selenium_url | selenium_mode |
		| BirminghamCityCouncil | None  | None  |

        @BlackburnCouncil
		Examples: BlackburnCouncil
		| council | selenium_url | selenium_mode |
		| BlackburnCouncil | http://selenium:4444  | local  |

        @BoltonCouncil
		Examples: BoltonCouncil
		| council | selenium_url | selenium_mode |
		| BoltonCouncil | http://selenium:4444  | local  |

        @BradfordMDC
		Examples: BradfordMDC
		| council | selenium_url | selenium_mode |
		| BradfordMDC | None  | None  |
  
        @BrightonandHoveCityCouncil
		Examples: BrightonandHoveCityCouncil
		| council | selenium_url | selenium_mode |
		| BrightonandHoveCityCouncil | http://selenium:4444  | local  |

        @BristolCityCouncil
		Examples: BristolCityCouncil
		| council | selenium_url | selenium_mode |
		| BristolCityCouncil | None  | None  |

        @BromleyBoroughCouncil
		Examples: BromleyBoroughCouncil
		| council | selenium_url | selenium_mode |
		| BromleyBoroughCouncil | http://selenium:4444  | local  |

        @BroxtoweBoroughCouncil
		Examples: BroxtoweBoroughCouncil
		| council | selenium_url | selenium_mode |
		| BroxtoweBoroughCouncil | http://selenium:4444  | local  |

        @BuckinghamshireCouncil
		Examples: BuckinghamshireCouncil
		| council | selenium_url | selenium_mode |
		| BuckinghamshireCouncil | http://selenium:4444  | local  |

        @BuryCouncil
		Examples: BuryCouncil
		| council | selenium_url | selenium_mode |
		| BuryCouncil | None  | None  |

        @CalderdaleCouncil
		Examples: CalderdaleCouncil
		| council | selenium_url | selenium_mode |
		| CalderdaleCouncil | http://selenium:4444  | local  |

        @CannockChaseDistrictCouncil
		Examples: CannockChaseDistrictCouncil
		| council | selenium_url | selenium_mode |
		| CannockChaseDistrictCouncil | None  | None  |

        @CardiffCouncil
		Examples: CardiffCouncil
		| council | selenium_url | selenium_mode |
		| CardiffCouncil | None  | None  |

        @CastlepointDistrictCouncil
		Examples: CastlepointDistrictCouncil
		| council | selenium_url | selenium_mode |
		| CastlepointDistrictCouncil | None  | None  |

        @CharnwoodBoroughCouncil
		Examples: CharnwoodBoroughCouncil
		| council | selenium_url | selenium_mode |
		| CharnwoodBoroughCouncil | None  | None  |

        @ChelmsfordCityCouncil
		Examples: ChelmsfordCityCouncil
		| council | selenium_url | selenium_mode |
		| ChelmsfordCityCouncil | http://selenium:4444  | local  |

        @CheshireEastCouncil
		Examples: CheshireEastCouncil
		| council | selenium_url | selenium_mode |
		| CheshireEastCouncil | None  | None  |

		@CheshireWestAndChesterCouncil
		Examples: CheshireWestAndChesterCouncil
		| council | selenium_url | selenium_mode |
		| CheshireWestAndChesterCouncil | http://selenium:4444  | local  |

        @ChorleyCouncil
		Examples: ChorleyCouncil
		| council | selenium_url | selenium_mode |
		| ChorleyCouncil | http://selenium:4444  | local  |

        @ConwyCountyBorough
		Examples: ConwyCountyBorough
		| council | selenium_url | selenium_mode |
		| ConwyCountyBorough | None  | None  |

        @CrawleyBoroughCouncil
		Examples: CrawleyBoroughCouncil
		| council | selenium_url | selenium_mode |
		| CrawleyBoroughCouncil | None  | None  |

        @CroydonCouncil
		Examples: CroydonCouncil
		| council | selenium_url | selenium_mode |
		| CroydonCouncil | None  | None  |

        @DerbyshireDalesDistrictCouncil
		Examples: DerbyshireDalesDistrictCouncil
		| council | selenium_url | selenium_mode |
		| DerbyshireDalesDistrictCouncil | http://selenium:4444  | local  |

        @DoncasterCouncil
		Examples: DoncasterCouncil
		| council | selenium_url | selenium_mode |
		| DoncasterCouncil | None  | None  |

        @DorsetCouncil
		Examples: DorsetCouncil
		| council | selenium_url | selenium_mode |
		| DorsetCouncil | None  | None  |

        @DoverDistrictCouncil
		Examples: DoverDistrictCouncil
		| council | selenium_url | selenium_mode |
		| DoverDistrictCouncil | None  | None  |

        @DurhamCouncil
		Examples: DurhamCouncil
		| council | selenium_url | selenium_mode |
		| DurhamCouncil | None  | None  |

        @EastCambridgeshireCouncil
		Examples: EastCambridgeshireCouncil
		| council | selenium_url | selenium_mode |
		| EastCambridgeshireCouncil | None  | None  |

        @EastDevonDC
		Examples: EastDevonDC
		| council | selenium_url | selenium_mode |
		| EastDevonDC | None  | None  |

        @EastleighBoroughCouncil
		Examples: EastleighBoroughCouncil
		| council | selenium_url | selenium_mode |
		| EastleighBoroughCouncil | None  | None  |

        @EastLindseyDistrictCouncil
		Examples: EastLindseyDistrictCouncil
		| council | selenium_url | selenium_mode |
		| EastLindseyDistrictCouncil | http://selenium:4444  | local  |

        @EastRidingCouncil
		Examples: EastRidingCouncil
		| council | selenium_url | selenium_mode |
		| EastRidingCouncil | http://selenium:4444  | local  |

        @EastSuffolkCouncil
		Examples: EastSuffolkCouncil
		| council | selenium_url | selenium_mode |
		| EastSuffolkCouncil | http://selenium:4444  | local  |

        @EnvironmentFirst
		Examples: EnvironmentFirst
		| council | selenium_url | selenium_mode |
		| EnvironmentFirst | None  | None  |

        @ErewashBoroughCouncil
		Examples: ErewashBoroughCouncil
		| council | selenium_url | selenium_mode |
		| ErewashBoroughCouncil | None  | None  |

        @FenlandDistrictCouncil
		Examples: FenlandDistrictCouncil
		| council | selenium_url | selenium_mode |
		| FenlandDistrictCouncil | None  | None  |

        @ForestOfDeanDistrictCouncil
		Examples: ForestOfDeanDistrictCouncil
		| council | selenium_url | selenium_mode |
		| ForestOfDeanDistrictCouncil | http://selenium:4444  | local  |

        @GatesheadCouncil
		Examples: GatesheadCouncil
		| council | selenium_url | selenium_mode |
		| GatesheadCouncil | http://selenium:4444  | local  |

        @GedlingBoroughCouncil
		Examples: GedlingBoroughCouncil
		| council | selenium_url | selenium_mode |
		| GedlingBoroughCouncil | None  | None  |

        @GlasgowCityCouncil
		Examples: GlasgowCityCouncil
		| council | selenium_url | selenium_mode |
		| GlasgowCityCouncil | None  | None  |

        @GuildfordCouncil
		Examples: GuildfordCouncil
		| council | selenium_url | selenium_mode |
		| GuildfordCouncil | http://selenium:4444  | local  |

        @HaltonBoroughCouncil
		Examples: HaltonBoroughCouncil
		| council | selenium_url | selenium_mode |
		| HaltonBoroughCouncil | http://selenium:4444  | local  |

        @HaringeyCouncil
		Examples: HaringeyCouncil
		| council | selenium_url | selenium_mode |
		| HaringeyCouncil | None  | None  |

        @HarrogateBoroughCouncil
		Examples: HarrogateBoroughCouncil
		| council | selenium_url | selenium_mode |
		| HarrogateBoroughCouncil | None  | None  |

        @HighPeakCouncil
		Examples: HighPeakCouncil
		| council | selenium_url | selenium_mode |
		| HighPeakCouncil | http://selenium:4444  | local  |

		@HullCityCouncil
		Examples: HullCityCouncil
		| council | selenium_url | selenium_mode |
		| HullCityCouncil | None  | None  |

        @HuntingdonDistrictCouncil
		Examples: HuntingdonDistrictCouncil
		| council | selenium_url | selenium_mode |
		| HuntingdonDistrictCouncil | None  | None  |

        @KingstonUponThamesCouncil
		Examples: KingstonUponThamesCouncil
		| council | selenium_url | selenium_mode |
		| KingstonUponThamesCouncil | None  | None  |

		@KirkleesCouncil
		Examples: KirkleesCouncil
		| council | selenium_url | selenium_mode |
		| KirkleesCouncil | http://selenium:4444  | local  |

		@KnowsleyMBCouncil
		Examples: KnowsleyMBCouncil
		| council | selenium_url | selenium_mode |
		| KnowsleyMBCouncil | http://selenium:4444  | local  |

        @LancasterCityCouncil
		Examples: LancasterCityCouncil
		| council | selenium_url | selenium_mode |
		| LancasterCityCouncil | None  | None  |

        @LeedsCityCouncil
		Examples: LeedsCityCouncil
		| council | selenium_url | selenium_mode |
		| LeedsCityCouncil | http://selenium:4444  | local  |

        @LisburnCastlereaghCityCouncil
		Examples: LisburnCastlereaghCityCouncil
		| council | selenium_url | selenium_mode |
		| LisburnCastlereaghCityCouncil | None  | None  |

        @LiverpoolCityCouncil
		Examples: LiverpoolCityCouncil
		| council | selenium_url | selenium_mode |
		| LiverpoolCityCouncil | None  | None  |

        @LondonBoroughHounslow
		Examples: LondonBoroughHounslow
		| council | selenium_url | selenium_mode |
		| LondonBoroughHounslow | None  | None  |

        @LondonBoroughRedbridge
		Examples: LondonBoroughRedbridge
		| council | selenium_url | selenium_mode |
		| LondonBoroughRedbridge | http://selenium:4444  | local  |
 
        @MaldonDistrictCouncil
		Examples: MaldonDistrictCouncil
		| council | selenium_url | selenium_mode |
		| MaldonDistrictCouncil | None  | None  |

        @MalvernHillsDC
		Examples: MalvernHillsDC
		| council | selenium_url | selenium_mode |
		| MalvernHillsDC | None  | None  |

        @ManchesterCityCouncil
		Examples: ManchesterCityCouncil
		| council | selenium_url | selenium_mode |
		| ManchesterCityCouncil | None  | None  |

		@MansfieldDistrictCouncil
		Examples: MansfieldDistrictCouncil
		| council | selenium_url | selenium_mode |
		| MansfieldDistrictCouncil | None  | None  |

        @MertonCouncil
		Examples: MertonCouncil
		| council | selenium_url | selenium_mode |
		| MertonCouncil | None  | None  |

        @MidAndEastAntrimBoroughCouncil
		Examples: MidAndEastAntrimBoroughCouncil
		| council | selenium_url | selenium_mode |
		| MidAndEastAntrimBoroughCouncil | http://selenium:4444  | local  |

        @MidSussexDistrictCouncil
		Examples: MidSussexDistrictCouncil
		| council | selenium_url | selenium_mode |
		| MidSussexDistrictCouncil | None  | None  |

        @MiltonKeynesCityCouncil
		Examples: MiltonKeynesCityCouncil
		| council | selenium_url | selenium_mode |
		| MiltonKeynesCityCouncil | None  | None  |

        @MoleValleyDistrictCouncil
        Examples: MoleValleyDistrictCouncil
        | council | selenium_url | selenium_mode |
        | MoleValleyDistrictCouncil | None | None |

        @NeathPortTalbotCouncil
		Examples: NeathPortTalbotCouncil
		| council | selenium_url | selenium_mode |
		| NeathPortTalbotCouncil | http://selenium:4444  | local  |

        @NewarkAndSherwoodDC
		Examples: NewarkAndSherwoodDC
		| council | selenium_url | selenium_mode |
		| NewarkAndSherwoodDC | None  | None  |

        @NewcastleCityCouncil
		Examples: NewcastleCityCouncil
		| council | selenium_url | selenium_mode |
		| NewcastleCityCouncil | None  | None  |

        @NewhamCouncil
		Examples: NewhamCouncil
		| council | selenium_url | selenium_mode |
		| NewhamCouncil | None  | None  |

        @NewportCityCouncil
		Examples: NewportCityCouncil
		| council | selenium_url | selenium_mode |
		| NewportCityCouncil | None  | None  |

        @NorthEastDerbyshireDistrictCouncil
		Examples: NorthEastDerbyshireDistrictCouncil
		| council | selenium_url | selenium_mode |
		| NorthEastDerbyshireDistrictCouncil | http://selenium:4444  | local  |

        @NorthEastLincs
		Examples: NorthEastLincs
		| council | selenium_url | selenium_mode |
		| NorthEastLincs | None  | None  |

        @NorthKestevenDistrictCouncil
		Examples: NorthKestevenDistrictCouncil
		| council | selenium_url | selenium_mode |
		| NorthKestevenDistrictCouncil | None  | None  |

        @NorthLanarkshireCouncil
		Examples: NorthLanarkshireCouncil
		| council | selenium_url | selenium_mode |
		| NorthLanarkshireCouncil | None  | None  |

        @NorthLincolnshireCouncil
		Examples: NorthLincolnshireCouncil
		| council | selenium_url | selenium_mode |
		| NorthLincolnshireCouncil | None  | None  |

        @NorthNorfolkDistrictCouncil
		Examples: NorthNorfolkDistrictCouncil
		| council | selenium_url | selenium_mode |
		| NorthNorfolkDistrictCouncil | http://selenium:4444  | local  |

        @NorthNorthamptonshireCouncil
		Examples: NorthNorthamptonshireCouncil
		| council | selenium_url | selenium_mode |
		| NorthNorthamptonshireCouncil | None  | None  |

        @NorthSomersetCouncil
		Examples: NorthSomersetCouncil
		| council | selenium_url | selenium_mode |
		| NorthSomersetCouncil | None  | None  |

        @NorthTynesideCouncil
		Examples: NorthTynesideCouncil
		| council | selenium_url | selenium_mode |
		| NorthTynesideCouncil | None  | None  |

        @NorthumberlandCouncil
		Examples: NorthumberlandCouncil
		| council | selenium_url | selenium_mode |
		| NorthumberlandCouncil | http://selenium:4444  | local  |

        @NorthWestLeicestershire
		Examples: NorthWestLeicestershire
		| council | selenium_url | selenium_mode |
		| NorthWestLeicestershire | http://selenium:4444  | local  |

		@NorthYorkshire
		Examples: NorthYorkshire
		| council | selenium_url | selenium_mode |
		| NorthYorkshire | None  | None  |

        @NottinghamCityCouncil
		Examples: NottinghamCityCouncil
		| council | selenium_url | selenium_mode |
		| NottinghamCityCouncil | None  | None  |

        @OldhamCouncil
		Examples: OldhamCouncil
		| council | selenium_url | selenium_mode |
		| OldhamCouncil | None  | None  |

        @PortsmouthCityCouncil
		Examples: PortsmouthCityCouncil
		| council | selenium_url | selenium_mode |
		| PortsmouthCityCouncil | http://selenium:4444  | local  |

        @PrestonCityCouncil
		Examples: PrestonCityCouncil
		| council | selenium_url | selenium_mode |
		| PrestonCityCouncil | http://selenium:4444  | local  |

        @ReadingBoroughCouncil
		Examples: ReadingBoroughCouncil
		| council | selenium_url | selenium_mode |
		| ReadingBoroughCouncil | None  | None  |

        @ReigateAndBansteadBoroughCouncil
		Examples: ReigateAndBansteadBoroughCouncil
		| council | selenium_url | selenium_mode |
		| ReigateAndBansteadBoroughCouncil | http://selenium:4444  | local  |

        @RenfrewshireCouncil
		Examples: RenfrewshireCouncil
		| council | selenium_url | selenium_mode |
		| RenfrewshireCouncil | http://selenium:4444  | local  |

        @RhonddaCynonTaffCouncil
		Examples: RhonddaCynonTaffCouncil
		| council | selenium_url | selenium_mode |
		| RhonddaCynonTaffCouncil | None  | None  |

        @RochdaleCouncil
		Examples: RochdaleCouncil
		| council | selenium_url | selenium_mode |
		| RochdaleCouncil | None  | None  |

		@RochfordCouncil
		Examples: RochfordCouncil
		| council | selenium_url | selenium_mode |
		| RochfordCouncil | None  | None  |

        @RugbyBoroughCouncil
		Examples: RugbyBoroughCouncil
		| council | selenium_url | selenium_mode |
		| RugbyBoroughCouncil | None  | None  |

        @RushcliffeBoroughCouncil
		Examples: RushcliffeBoroughCouncil
		| council | selenium_url | selenium_mode |
		| RushcliffeBoroughCouncil | http://selenium:4444  | local  |

        @RushmoorCouncil
		Examples: RushmoorCouncil
		| council | selenium_url | selenium_mode |
		| RushmoorCouncil | None  | None  |

        @SalfordCityCouncil
		Examples: SalfordCityCouncil
		| council | selenium_url | selenium_mode |
		| SalfordCityCouncil | None  | None  |

        @SevenoaksDistrictCouncil
		Examples: SevenoaksDistrictCouncil
		| council | selenium_url | selenium_mode |
		| SevenoaksDistrictCouncil | http://selenium:4444  | local  |

        @SheffieldCityCouncil
		Examples: SheffieldCityCouncil
		| council | selenium_url | selenium_mode |
		| SheffieldCityCouncil | None  | None  |

        @ShropshireCouncil
		Examples: ShropshireCouncil
		| council | selenium_url | selenium_mode |
		| ShropshireCouncil | None  | None  |

		@SolihullCouncil
		Examples: SolihullCouncil
		| council | selenium_url | selenium_mode |
		| SolihullCouncil | None  | None  |

        @SomersetCouncil
		Examples: SomersetCouncil
		| council | selenium_url | selenium_mode |
		| SomersetCouncil | None  | None  |

        @SouthAyrshireCouncil
		Examples: SouthAyrshireCouncil
		| council | selenium_url | selenium_mode |
		| SouthAyrshireCouncil | None  | None  |

        @SouthCambridgeshireCouncil
		Examples: SouthCambridgeshireCouncil
		| council | selenium_url | selenium_mode |
		| SouthCambridgeshireCouncil | None  | None  |

        @SouthGloucestershireCouncil
		Examples: SouthGloucestershireCouncil
		| council | selenium_url | selenium_mode |
		| SouthGloucestershireCouncil | None  | None  |

        @SouthLanarkshireCouncil
		Examples: SouthLanarkshireCouncil
		| council | selenium_url | selenium_mode |
		| SouthLanarkshireCouncil | None  | None  |

        @SouthNorfolkCouncil
		Examples: SouthNorfolkCouncil
		| council | selenium_url | selenium_mode |
		| SouthNorfolkCouncil | None  | None  |

        @SouthOxfordshireCouncil
		Examples: SouthOxfordshireCouncil
		| council | selenium_url | selenium_mode |
		| SouthOxfordshireCouncil | None  | None  |

        @SouthTynesideCouncil
		Examples: SouthTynesideCouncil
		| council | selenium_url | selenium_mode |
		| SouthTynesideCouncil | None  | None  |

        @StAlbansCityAndDistrictCouncil
        Examples: StAlbansCityAndDistrictCouncil
        | council | selenium_url | selenium_mode |
        | StAlbansCityAndDistrictCouncil | None  | None  |

        @StaffordshireMoorlandsDistrictCouncil
		Examples: StaffordshireMoorlandsDistrictCouncil
		| council | selenium_url | selenium_mode |
		| StaffordshireMoorlandsDistrictCouncil | http://selenium:4444  | local  |

        @StHelensBC
		Examples: StHelensBC
		| council | selenium_url | selenium_mode |
		| StHelensBC | None  | None  |

        @StockportBoroughCouncil
		Examples: StockportBoroughCouncil
		| council | selenium_url | selenium_mode |
		| StockportBoroughCouncil | None  | None  |

        @StokeOnTrentCityCouncil
		Examples: StokeOnTrentCityCouncil
		| council | selenium_url | selenium_mode |
		| StokeOnTrentCityCouncil | None  | None  |

        @StratfordUponAvonCouncil
		Examples: StratfordUponAvonCouncil
		| council | selenium_url | selenium_mode |
		| StratfordUponAvonCouncil | None  | None  |

		@SunderlandCityCouncil
		Examples: SunderlandCityCouncil
		| council | selenium_url | selenium_mode |
		| SunderlandCityCouncil | http://selenium:4444  | local  |

        @SwaleBoroughCouncil
		Examples: SwaleBoroughCouncil
		| council | selenium_url | selenium_mode |
		| SwaleBoroughCouncil | None  | None  |

        @TamesideMBCouncil
		Examples: TamesideMBCouncil
		| council | selenium_url | selenium_mode |
		| TamesideMBCouncil | None  | None  |

		@TandridgeDistrictCouncil
		Examples: TandridgeDistrictCouncil
		| council | selenium_url | selenium_mode |
		| TandridgeDistrictCouncil | None  | None  |

		@TelfordAndWrekinCouncil
		Examples: TelfordAndWrekinCouncil
		| council | selenium_url | selenium_mode |
		| TelfordAndWrekinCouncil | None  | None  |

        @TestValleyBoroughCouncil
		Examples: TestValleyBoroughCouncil
		| council | selenium_url | selenium_mode |
		| TestValleyBoroughCouncil | None  | None  |

        @TonbridgeAndMallingBC
		Examples: TonbridgeAndMallingBC
		| council | selenium_url | selenium_mode |
		| TonbridgeAndMallingBC | None  | None  |

        @TorbayCouncil
		Examples: TorbayCouncil
		| council | selenium_url | selenium_mode |
		| TorbayCouncil | None  | None  |

        @TorridgeDistrictCouncil
		Examples: TorridgeDistrictCouncil
		| council | selenium_url | selenium_mode |
		| TorridgeDistrictCouncil | None  | None  |

        @ValeofGlamorganCouncil
		Examples: ValeofGlamorganCouncil
		| council | selenium_url | selenium_mode |
		| ValeofGlamorganCouncil | None  | None  |

        @ValeofWhiteHorseCouncil
		Examples: ValeofWhiteHorseCouncil
		| council | selenium_url | selenium_mode |
		| ValeofWhiteHorseCouncil | None  | None  |

        @WakefieldCityCouncil
		Examples: WakefieldCityCouncil
		| council | selenium_url | selenium_mode |
		| WakefieldCityCouncil | http://selenium:4444  | local  |

        @WarwickDistrictCouncil
		Examples: WarwickDistrictCouncil
		| council | selenium_url | selenium_mode |
		| WarwickDistrictCouncil | None  | None  |

        @WaverleyBoroughCouncil
		Examples: WaverleyBoroughCouncil
		| council | selenium_url | selenium_mode |
		| WaverleyBoroughCouncil | None  | None  |

        @WealdenDistrictCouncil
		Examples: WealdenDistrictCouncil
		| council | selenium_url | selenium_mode |
		| WealdenDistrictCouncil | None  | None  |

        @WelhatCouncil
		Examples: WelhatCouncil
		| council | selenium_url | selenium_mode |
		| WelhatCouncil | None  | None  |

		@WestBerkshireCouncil
		Examples: WestBerkshireCouncil
		| council | selenium_url | selenium_mode |
		| WestBerkshireCouncil | http://selenium:4444  | local  |

        @WestLindseyDistrictCouncil
		Examples: WestLindseyDistrictCouncil
		| council | selenium_url | selenium_mode |
		| WestLindseyDistrictCouncil | None  | None  |

        @WestLothianCouncil
		Examples: WestLothianCouncil
		| council | selenium_url | selenium_mode |
		| WestLothianCouncil | http://selenium:4444  | local  |

		@WestNorthamptonshireCouncil
		Examples: WestNorthamptonshireCouncil
		| council | selenium_url | selenium_mode |
		| WestNorthamptonshireCouncil | None  | None  |

        @WestSuffolkCouncil
		Examples: WestSuffolkCouncil
		| council | selenium_url | selenium_mode |
		| WestSuffolkCouncil | http://selenium:4444  | local  |

        @WiganBoroughCouncil
		Examples: WiganBoroughCouncil
		| council | selenium_url | selenium_mode |
		| WiganBoroughCouncil | None  | None  |

        @WiltshireCouncil
		Examples: WiltshireCouncil
		| council | selenium_url | selenium_mode |
		| WiltshireCouncil | None  | None  |

        @WindsorAndMaidenheadCouncil
		Examples: WindsorAndMaidenheadCouncil
		| council | selenium_url | selenium_mode |
		| WindsorAndMaidenheadCouncil | None  | None  |

        @WokingBoroughCouncil
		Examples: WokingBoroughCouncil
		| council | selenium_url | selenium_mode |
		| WokingBoroughCouncil | None  | None  |

		@WyreCouncil
		Examples: WyreCouncil
		| council | selenium_url | selenium_mode |
		| WyreCouncil | None  | None  |

        @YorkCouncil
		Examples: YorkCouncil
		| council | selenium_url | selenium_mode |
		| YorkCouncil | None  | None  |
