import geopandas as gpd
import folium
import osmnx as ox
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def get_tangier_data():
    try:
        # Charger les limites de la ville de Tanger
        city = ox.geocode_to_gdf('Tangier, Morocco')
        city_projected = city.to_crs(epsg=32629)

        # Charger les espaces verts avec plus de détails
        green_spaces = ox.features_from_place(
            'Tangier, Morocco',
            tags={
                'leisure': ['park', 'garden', 'nature_reserve', 'pitch', 'golf_course'],
                'landuse': ['grass', 'forest', 'recreation_ground', 'green', 'meadow', 'orchard'],
                'natural': ['grassland', 'wood', 'scrub']
            }
        )
        green_spaces = green_spaces[green_spaces.geometry.notnull()]
        green_spaces['geometry'] = green_spaces['geometry'].apply(lambda geom: geom if geom.is_valid else geom.buffer(0))

        # Reprojeter les espaces verts et filtrer les géométries Polygon uniquement
        green_spaces_projected = green_spaces.to_crs(epsg=32629)
        green_spaces_projected = green_spaces_projected[green_spaces_projected.geometry.type.isin(['Polygon', 'MultiPolygon'])]

        # Intersecter les espaces verts avec les limites de la ville
        green_spaces_within_city = green_spaces_projected.overlay(city_projected, how='intersection') if not green_spaces_projected.empty else gpd.GeoDataFrame()

        # Charger les zones urbaines avec plus de détails
        urban_areas = ox.features_from_place(
            'Tangier, Morocco',
            tags={'landuse': ['residential', 'commercial', 'industrial', 'urban'], 'building': True}
        )
        urban_areas = urban_areas[urban_areas.geometry.notnull()]
        urban_areas['geometry'] = urban_areas['geometry'].apply(lambda geom: geom if geom.is_valid else geom.buffer(0))

        urban_areas_projected = urban_areas.to_crs(epsg=32629)
        urban_areas_projected = urban_areas_projected[urban_areas_projected.geometry.type.isin(['Polygon', 'MultiPolygon'])]

        # Intersecter les zones urbaines avec les limites de la ville
        urban_areas_within_city = urban_areas_projected.overlay(city_projected, how='intersection') if not urban_areas_projected.empty else gpd.GeoDataFrame()

        # Calculer les surfaces
        city_area = city_projected.geometry.area.sum()
        green_area = green_spaces_within_city.geometry.area.sum() if not green_spaces_within_city.empty else 0
        urban_area = urban_areas_within_city.geometry.area.sum() if not urban_areas_within_city.empty else 0

        green_percentage = (green_area / city_area) * 100 if city_area > 0 else 0
        urban_percentage = (urban_area / city_area) * 100 if city_area > 0 else 0

        # Préparer les données pour les CSV
        def prepare_green_spaces_data(gdf):
            green_data = []
            for index, row in gdf.iterrows():
                centroid = row.geometry.centroid
                name_columns = ['name', 'name:fr', 'name:en', 'name:ar', 'designation']
                name = next((row.get(col) for col in name_columns if row.get(col)), f'Espace vert {index}')
                green_data.append({
                    'Nom': name,
                    'Type': row.get('leisure', row.get('landuse', row.get('natural', 'Non spécifié'))),
                    'Latitude': centroid.y,
                    'Longitude': centroid.x,
                    'Superficie_m2': row.geometry.area
                })
            return pd.DataFrame(green_data)

        def prepare_urban_areas_data(gdf):
            urban_data = []
            for index, row in gdf.iterrows():
                centroid = row.geometry.centroid
                name_columns = ['name', 'name:fr', 'name:en', 'name:ar']
                name = next((row.get(col) for col in name_columns if row.get(col)), f'Zone urbaine {index}')
                urban_data.append({
                    'Zone': name,
                    'Type': row.get('landuse', row.get('building', 'Non spécifié')),
                    'Latitude': centroid.y,
                    'Longitude': centroid.x,
                    'Superficie_m2': row.geometry.area
                })
            return pd.DataFrame(urban_data)

        # Générer les DataFrames
        green_spaces_df = prepare_green_spaces_data(green_spaces_within_city)
        urban_areas_df = prepare_urban_areas_data(urban_areas_within_city)

        # Sauvegarder les CSV
        green_spaces_df.to_csv('tangier_green_spaces.csv', index=False, encoding='utf-8')
        urban_areas_df.to_csv('tangier_urban_areas.csv', index=False, encoding='utf-8')

        # Créer une carte interactive
        m = folium.Map(location=[35.7595, -5.8340], zoom_start=12)
        folium.GeoJson(city, name='City Boundary').add_to(m)
        # Ajouter les limites de la ville (rouge)
        folium.GeoJson(
            city,
            name='Limites de la ville',
            style_function=lambda x: {
                'fillColor': 'none',  # Pas de remplissage
                'color': 'red',  # Contour en rouge
                'weight': 2,  # Épaisseur du contour
                'fillOpacity': 0  # Opacité du remplissage (aucun remplissage)
            },
            tooltip="Limites de la ville de Tanger"
        ).add_to(m)

        if not green_spaces_within_city.empty:
            folium.GeoJson(
                green_spaces_within_city,
                name='Espaces verts',
                style_function=lambda x: {'fillColor': 'green', 'color': 'green', 'weight': 1}
            ).add_to(m)

        if not urban_areas_within_city.empty:
            folium.GeoJson(
                urban_areas_within_city,
                name='Zones urbaines',
                style_function=lambda x: {'fillColor': 'blue', 'color': 'blue', 'weight': 1}
            ).add_to(m)
        # Ajouter des points pour les espaces verts
        if not green_spaces_within_city.empty:
            for idx, row in green_spaces_df.iterrows():
                folium.Marker(
                    location=[row['Latitude'], row['Longitude']],
                    popup=f"Nom : {row['Nom']}<br>Type : {row['Type']}<br>Superficie : {row['Superficie_m2']:.2f} m²",
                    icon=folium.Icon(color='green', icon='tree-conifer', prefix='glyphicon')
                ).add_to(m)

        # Ajouter des points pour les zones urbaines
        if not urban_areas_within_city.empty:
            for idx, row in urban_areas_df.iterrows():
                folium.Marker(
                    location=[row['Latitude'], row['Longitude']],
                    popup=f"Nom : {row['Zone']}<br>Type : {row['Type']}<br>Superficie : {row['Superficie_m2']:.2f} m²",
                    icon=folium.Icon(color='blue', icon='info-sign', prefix='glyphicon')
                ).add_to(m)

        folium.LayerControl().add_to(m)
        m.save('tangier_map_analysis.html')

        # Ajouter des visualisations supplémentaires
        data = pd.DataFrame({
            'Catégorie': ['Espaces verts', 'Zones urbaines', 'Autres'],
            'Superficie (km²)': [green_area / 1e6, urban_area / 1e6, (city_area - green_area - urban_area) / 1e6]
        })

        # Diagramme circulaire (existant)
        plt.figure(figsize=(8, 8))
        plt.pie(
            data['Superficie (km²)'],
            labels=data['Catégorie'],
            autopct='%1.1f%%',
            colors=['green', 'blue', 'gray']
        )
        plt.title('Répartition des zones à Tanger')
        plt.savefig('area_distribution_pie_chart.png')
        plt.close()

        # Graphique en barres
        plt.figure(figsize=(10, 6))
        sns.barplot(data=data, x='Catégorie', y='Superficie (km²)', palette=['green', 'blue', 'gray'])
        plt.title('Distribution des surfaces à Tanger')
        plt.ylabel('Superficie (km²)')
        plt.xlabel('Catégorie')
        plt.savefig('tangier_area_distribution.png')
        plt.close()

        return {
            'city_name': 'Tangier',
            'coordinates': {'lat': 35.7595, 'lon': -5.8340},
            'total_area_km2': city_area / 1e6,
            'green_space_percentage': green_percentage,
            'urban_percentage': urban_percentage,
        }

    except Exception as e:
        print(f"Erreur lors de l'exécution : {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    results = get_tangier_data()
    if results:
        print("\n--- Résultats de l'analyse ---")
        print(f"Ville : {results['city_name']}")
        print(f"Coordonnées : {results['coordinates']}")
        print(f"Superficie totale : {results['total_area_km2']:.2f} km²")
        print(f"Espaces verts : {results['green_space_percentage']:.2f}%")
        print(f"Zones urbaines : {results['urban_percentage']:.2f}%")
        print("\nFichiers générés :")
        print("1. tangier_green_spaces.csv")
        print("2. tangier_urban_areas.csv")
        print("3. tangier_map_analysis.html")
        print("4. area_distribution_pie_chart.png")
        print("5. tangier_area_distribution.png")


main()